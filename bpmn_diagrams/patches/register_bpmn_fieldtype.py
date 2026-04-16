from __future__ import annotations

from collections.abc import Iterable


def execute():
	import frappe
	import frappe.model as model

	if "BPMN" not in model.data_fieldtypes:
		model.data_fieldtypes = model.data_fieldtypes + ("BPMN",)

	if getattr(frappe, "db", None) and hasattr(frappe.db, "type_map"):
		db_type = frappe.conf.get("db_type", "mariadb")
		if db_type == "postgres":
			frappe.db.type_map["BPMN"] = ("text", "")
		elif db_type == "sqlite":
			frappe.db.type_map["BPMN"] = ("TEXT", None)
		else:
			frappe.db.type_map["BPMN"] = ("longtext", "")

	_ensure_bpmn_columns()
	_ensure_docfield_fieldtype_option()


def _ensure_bpmn_columns():
	import frappe

	docfield = frappe.qb.DocType("DocField")
	doctype = frappe.qb.DocType("DocType")
	bpmn_fields = (
		frappe.qb.from_(docfield)
		.join(doctype)
		.on(doctype.name == docfield.parent)
		.select(docfield.parent, docfield.fieldname)
		.where((docfield.fieldtype == "BPMN") & (doctype.issingle == 0))
	).run(as_dict=True)

	for field in bpmn_fields:
		table_name = f"tab{field['parent']}"
		column_name = field["fieldname"]
		if not _column_exists(table_name, column_name):
			frappe.db.sql(
				f"ALTER TABLE {_quote_identifier(table_name)} ADD COLUMN {_quote_identifier(column_name)} {_column_type()}"
			)


def _column_exists(table_name: str, column_name: str) -> bool:
	import frappe

	db_type = frappe.conf.get("db_type", "mariadb")
	if db_type == "postgres":
		result = frappe.db.sql(
			"""
			SELECT 1
			FROM information_schema.columns
			WHERE table_schema = current_schema()
			  AND table_name = %s
			  AND column_name = %s
			""",
			(table_name, column_name),
		)
	elif db_type == "sqlite":
		result = _sqlite_table_info(table_name)
		return any(column[1] == column_name for column in result)
	else:
		result = frappe.db.sql(f"SHOW COLUMNS FROM `{table_name}` LIKE %s", column_name)  # noqa: S608

	return bool(result)


def _sqlite_table_info(table_name: str) -> Iterable[tuple]:
	import frappe

	return frappe.db.sql(f"PRAGMA table_info({_quote_identifier(table_name)})")  # noqa: S608


def _ensure_docfield_fieldtype_option():
	import frappe

	for doctype_name in ("DocField", "Custom Field", "Customize Form Field"):
		_ensure_fieldtype_option_for_doctype(doctype_name)


def _ensure_fieldtype_option_for_doctype(doctype_name: str):
	import frappe

	property_setter_name = f"{doctype_name}-fieldtype-options"
	if frappe.db.exists("Property Setter", property_setter_name):
		current_value = frappe.db.get_value("Property Setter", property_setter_name, "value") or ""
		if "BPMN" not in current_value.splitlines():
			frappe.db.set_value(
				"Property Setter",
				property_setter_name,
				"value",
				_with_bpmn_option(current_value),
			)
		return

	options_value = _with_bpmn_option(_current_fieldtype_options(doctype_name))

	frappe.get_doc(
		{
			"doctype": "Property Setter",
			"name": property_setter_name,
			"doc_type": doctype_name,
			"field_name": "fieldtype",
			"property": "options",
			"property_type": "Text",
			"value": options_value,
		}
	).insert(ignore_permissions=True)


def _current_fieldtype_options(doctype_name: str) -> str:
	import frappe

	return frappe.get_meta(doctype_name).get_field("fieldtype").options or ""


def _with_bpmn_option(options: str) -> str:
	lines = [line for line in options.splitlines() if line]
	if "BPMN" in lines:
		return options

	insert_after = "Barcode"
	if insert_after in lines:
		lines.insert(lines.index(insert_after) + 1, "BPMN")
	else:
		lines.append("BPMN")

	return "\n".join(lines)


def _column_type() -> str:
	import frappe

	db_type = frappe.conf.get("db_type", "mariadb")
	if db_type == "postgres":
		return "TEXT"
	if db_type == "sqlite":
		return "TEXT"
	return "LONGTEXT"


def _quote_identifier(identifier: str) -> str:
	import frappe

	db_type = frappe.conf.get("db_type", "mariadb")
	escaped = identifier.replace('"', '""')
	if db_type == "mariadb":
		return f"`{identifier}`"
	return f'"{escaped}"'
