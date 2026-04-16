import Modeler from "bpmn-js/lib/Modeler";

const EMPTY_DIAGRAM_XML = `<?xml version="1.0" encoding="UTF-8"?>
<bpmn:definitions xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
	xmlns:bpmn="http://www.omg.org/spec/BPMN/20100524/MODEL"
	xmlns:bpmndi="http://www.omg.org/spec/BPMN/20100524/DI"
	xmlns:dc="http://www.omg.org/spec/DD/20100524/DC"
	xmlns:di="http://www.omg.org/spec/DD/20100524/DI"
	id="Definitions_1"
	targetNamespace="http://bpmn.io/schema/bpmn">
	<bpmn:process id="Process_1" isExecutable="false">
		<bpmn:startEvent id="StartEvent_1" />
	</bpmn:process>
	<bpmndi:BPMNDiagram id="BPMNDiagram_1">
		<bpmndi:BPMNPlane id="BPMNPlane_1" bpmnElement="Process_1">
			<bpmndi:BPMNShape id="StartEvent_1_di" bpmnElement="StartEvent_1">
				<dc:Bounds x="179" y="99" width="36" height="36" />
			</bpmndi:BPMNShape>
		</bpmndi:BPMNPlane>
	</bpmndi:BPMNDiagram>
</bpmn:definitions>`;

const BPMN_STYLESHEET_ID = "bpmn-diagrams-fieldtype-css";
const BPMN_STYLESHEET_URL = "/assets/bpmn_diagrams/css/bpmn_fieldtype.css";

function debounce(fn, wait) {
	let timeoutId = null;

	return function debounced(...args) {
		window.clearTimeout(timeoutId);
		timeoutId = window.setTimeout(() => fn.apply(this, args), wait);
	};
}

function normalize_xml(xml) {
	return (xml || "").trim();
}

function coerce_bpmn_xml(value) {
	if (typeof value !== "string") {
		return "";
	}

	const xml = value.trim();
	if (!xml) {
		return "";
	}

	if (xml.startsWith("<?xml") || xml.startsWith("<bpmn:definitions") || xml.startsWith("<bpmn:Definitions")) {
		return value;
	}

	return "";
}

function get_bpmn_controls(frm) {
	return Object.values(frm.fields_dict || {}).filter((field) => field?.df?.fieldtype === "BPMN");
}

function get_field_value(field) {
	if (typeof field.value === "string") {
		return field.value;
	}

	if (field.frm?.doc) {
		return field.frm.doc[field.df.fieldname];
	}

	if (field.doc) {
		return field.doc[field.df.fieldname];
	}

	return "";
}

function ensure_bpmn_stylesheet() {
	if (document.getElementById(BPMN_STYLESHEET_ID)) {
		return;
	}

	const link = document.createElement("link");
	link.id = BPMN_STYLESHEET_ID;
	link.rel = "stylesheet";
	link.href = BPMN_STYLESHEET_URL;
	document.head.appendChild(link);
}

frappe.ui.form.ControlBPMN = class ControlBPMN extends frappe.ui.form.ControlData {
	static html_element = "textarea";
	static horizontal = false;
	static trigger_change_on_input_event = false;

	async serialize_diagram(force_set_value = false) {
		if (!this.modeler || this._importing_xml) {
			return;
		}

		try {
			const { xml } = await this.modeler.saveXML({ format: true });
			this.last_xml = xml;
			this.last_imported_xml = xml;
			this.$input.val(xml);

			if (this.frm) {
				this.frm.doc[this.df.fieldname] = xml;
			} else if (this.doc) {
				this.doc[this.df.fieldname] = xml;
			}

			this.value = xml;
			await this.validate_and_set_in_model(xml, null, force_set_value);
			this.set_status(__("Diagram ready"));
		} catch (error) {
			this.set_status(__("Unable to serialize BPMN XML"), true);
			console.error("Failed to save BPMN XML", error);
			throw error;
		}
	}

	make_input() {
		if (this.$input) {
			return;
		}

		ensure_bpmn_stylesheet();
		super.make_input();

		this.$input.addClass("bpmn-xml-input");

		this.$modeler = $(`
			<div class="bpmn-control">
				<div class="bpmn-control__toolbar">
					<div class="bpmn-control__status text-muted small"></div>
					<button class="btn btn-xs btn-default bpmn-control__fit" type="button">
						${__("Fit")}
					</button>
				</div>
				<div class="bpmn-control__canvas"></div>
			</div>
		`).appendTo(this.input_area);

		this.$status = this.$modeler.find(".bpmn-control__status");
		this.$canvas = this.$modeler.find(".bpmn-control__canvas");

		this.$modeler.find(".bpmn-control__fit").on("click", () => this.fit_viewport());

		this.modeler = new Modeler({
			container: this.$canvas.get(0),
		});

		this.push_xml_to_model = debounce(async () => {
			if (this._importing_xml || this.disp_status !== "Write") {
				return;
			}

			await this.serialize_diagram();
		}, 400);

		this.modeler.on("commandStack.changed", () => {
			if (this._importing_xml || this.disp_status !== "Write") {
				return;
			}

			if (this.frm && !this.frm.is_dirty()) {
				this.frm.dirty();
			}

			this.push_xml_to_model();
		});
	}

	async refresh_input() {
		await super.refresh_input();

		if (this.modeler && !this._importing_xml) {
			const latest_value = get_field_value(this);
			const normalized_latest = normalize_xml(coerce_bpmn_xml(latest_value));
			const normalized_imported = normalize_xml(this.last_imported_xml);

			if ((normalized_latest || !this.last_imported_xml) && normalized_latest !== normalized_imported) {
				await this.set_input(latest_value);
			}
		}

		if (this.modeler && this.disp_status === "Write") {
			this.$modeler.removeClass("hide");
			this.$input.addClass("bpmn-xml-input");
			window.requestAnimationFrame(() => {
				this.modeler.get("canvas").resized();
				if (this.should_fit_viewport) {
					this.fit_viewport();
					this.should_fit_viewport = false;
				}
			});
		}
	}

	async set_input(value) {
		super.set_input(value);

		if (!this.modeler) {
			return;
		}

		const incoming_xml = coerce_bpmn_xml(value);
		const xml = incoming_xml || EMPTY_DIAGRAM_XML;
		const normalized_xml = normalize_xml(xml);
		const current_xml = normalize_xml(this.last_xml || this.$input.val());
		const imported_xml = normalize_xml(this.last_imported_xml);

		if (normalized_xml && imported_xml && (normalized_xml === current_xml || normalized_xml === imported_xml)) {
			this.$input.val(xml);
			this.last_xml = xml;
			this.last_imported_xml = xml;
			return;
		}

		this._importing_xml = true;
		this.set_status(__("Loading diagram..."));

		try {
			await this.modeler.importXML(xml);
			this.last_imported_xml = xml;
			this.last_xml = xml;
			this.should_fit_viewport = true;
			this.sync_canvas_viewport();
			this.$input.val(xml);
			this.set_status(__("Diagram ready"));

			if (!incoming_xml && this.disp_status === "Write") {
				const { xml: serializedXml } = await this.modeler.saveXML({ format: true });
				this.last_imported_xml = serializedXml;
				this.last_xml = serializedXml;
				this.$input.val(serializedXml);
				await this.validate_and_set_in_model(serializedXml, null, true);
			}
		} catch (error) {
			this.set_status(__("Unable to load BPMN diagram"), true);
			console.error("Failed to import BPMN XML", error);
		} finally {
			this._importing_xml = false;
		}
	}

	set_status(message, isError = false) {
		if (!this.$status) {
			return;
		}

		this.$status
			.text(message || "")
			.toggleClass("text-danger", isError)
			.toggleClass("text-muted", !isError);
	}

	sync_canvas_viewport() {
		if (!this.modeler) {
			return;
		}

		window.requestAnimationFrame(() => {
			const canvas = this.modeler.get("canvas");
			canvas.resized();
			canvas.zoom("fit-viewport", "auto");
		});
	}

	fit_viewport() {
		if (!this.modeler) {
			return;
		}

		const canvas = this.modeler.get("canvas");
		canvas.zoom("fit-viewport", "auto");
	}
};

if (!frappe.model.all_fieldtypes.includes("BPMN")) {
	const insertAfter = frappe.model.all_fieldtypes.indexOf("Barcode");
	if (insertAfter >= 0) {
		frappe.model.all_fieldtypes.splice(insertAfter + 1, 0, "BPMN");
	} else {
		frappe.model.all_fieldtypes.push("BPMN");
	}
}

if (!window.__bpmn_before_save_registered) {
	frappe.ui.form.on("*", {
		async before_save(frm) {
			for (const field of get_bpmn_controls(frm)) {
				if (typeof field.serialize_diagram === "function") {
					await field.serialize_diagram(true);
				}
			}
		},
	});

	window.__bpmn_before_save_registered = true;
}

if (!window.__bpmn_save_request_patched) {
	const original_save = frappe.ui.form.save;

	frappe.ui.form.save = function patched_bpmn_save(frm, action, callback, btn) {
		const flush = async () => {
			for (const field of get_bpmn_controls(frm)) {
				if (typeof field.serialize_diagram === "function") {
					await field.serialize_diagram(true);
				}
			}
		};

		return Promise.resolve(flush()).then(() => original_save.call(this, frm, action, callback, btn));
	};

	window.__bpmn_save_request_patched = true;
}
