import frappe.model as _model

__version__ = "0.0.3"

_BPMN_DB_TYPES = {
	"mariadb": ("longtext", ""),
	"postgres": ("text", ""),
	"sqlite": ("TEXT", None),
}


def _register_bpmn_data_fieldtype():
	if "BPMN" not in _model.data_fieldtypes:
		_model.data_fieldtypes = _model.data_fieldtypes + ("BPMN",)


def _patch_imported_data_fieldtypes():
	for module_path in (
		"frappe.model.meta",
		"frappe.model.create_new",
		"frappe.core.report.permitted_documents_for_user.permitted_documents_for_user",
	):
		try:
			module = __import__(module_path, fromlist=["data_fieldtypes"])
			module.data_fieldtypes = _model.data_fieldtypes
		except Exception:
			pass


def _patch_db_type_map():
	for module_path in (
		"frappe.database.mariadb.database",
		"frappe.database.mariadb.mysqlclient",
	):
		try:
			module = __import__(module_path, fromlist=["MariaDBDatabase"])
			mariadb_class = module.MariaDBDatabase

			if not getattr(mariadb_class.setup_type_map, "_bpmn_patched", False):
				_original_mariadb_setup = mariadb_class.setup_type_map

				def _patched_mariadb_setup(self):
					_original_mariadb_setup(self)
					self.type_map.setdefault("BPMN", _BPMN_DB_TYPES["mariadb"])

				_patched_mariadb_setup._bpmn_patched = True
				mariadb_class.setup_type_map = _patched_mariadb_setup
		except ImportError:
			pass

	try:
		from frappe.database.postgres.database import PostgresDatabase

		if not getattr(PostgresDatabase.setup_type_map, "_bpmn_patched", False):
			_original_postgres_setup = PostgresDatabase.setup_type_map

			def _patched_postgres_setup(self):
				_original_postgres_setup(self)
				self.type_map.setdefault("BPMN", _BPMN_DB_TYPES["postgres"])

			_patched_postgres_setup._bpmn_patched = True
			PostgresDatabase.setup_type_map = _patched_postgres_setup
	except ImportError:
		pass

	try:
		from frappe.database.sqlite.database import SQLiteDatabase

		if not getattr(SQLiteDatabase.setup_type_map, "_bpmn_patched", False):
			_original_sqlite_setup = SQLiteDatabase.setup_type_map

			def _patched_sqlite_setup(self):
				_original_sqlite_setup(self)
				self.type_map.setdefault("BPMN", _BPMN_DB_TYPES["sqlite"])

			_patched_sqlite_setup._bpmn_patched = True
			SQLiteDatabase.setup_type_map = _patched_sqlite_setup
	except ImportError:
		pass

	try:
		import frappe as _frappe

		if getattr(_frappe, "db", None) and hasattr(_frappe.db, "type_map"):
			db_type = _frappe.conf.get("db_type", "mariadb")
			_frappe.db.type_map.setdefault("BPMN", _BPMN_DB_TYPES.get(db_type, _BPMN_DB_TYPES["mariadb"]))
	except Exception:
		pass


def _patch_docfield_meta():
	try:
		from frappe.model.meta import Meta

		if getattr(Meta.process, "_bpmn_patched", False):
			return

		_original_process = Meta.process

		def _patched_process(self):
			_original_process(self)

			for field in getattr(self, "fields", []) or []:
				if getattr(field, "fieldtype", None) == "BPMN":
					field.ignore_xss_filter = 1

			if self.name not in {"DocField", "Custom Field", "Customize Form Field"}:
				return

			fieldtype_field = self.get_field("fieldtype")
			if not fieldtype_field:
				return

			options = fieldtype_field.options or ""
			if "BPMN" not in options.splitlines():
				fieldtype_field.options = f"{options}\nBPMN" if options else "BPMN"

		_patched_process._bpmn_patched = True
		Meta.process = _patched_process
	except Exception:
		pass


def _patch_content_sanitizer():
	try:
		from frappe.model.base_document import BaseDocument

		if getattr(BaseDocument._sanitize_content, "_bpmn_patched", False):
			return

		_original_sanitize_content = BaseDocument._sanitize_content

		def _patched_sanitize_content(self):
			bpmn_fields = []
			for field in getattr(self.meta, "fields", []) or []:
				if getattr(field, "fieldtype", None) == "BPMN":
					bpmn_fields.append((field, getattr(field, "ignore_xss_filter", None)))
					field.ignore_xss_filter = 1

			try:
				return _original_sanitize_content(self)
			finally:
				for field, original_value in bpmn_fields:
					field.ignore_xss_filter = original_value

		_patched_sanitize_content._bpmn_patched = True
		BaseDocument._sanitize_content = _patched_sanitize_content
	except Exception:
		pass


def _clear_bpmn_meta_caches():
	try:
		import frappe as _frappe
		from frappe.model.meta import clear_meta_cache

		if getattr(_frappe, "local", None):
			clear_meta_cache()
			if hasattr(_frappe.local, "valid_columns"):
				_frappe.local.valid_columns = {}
	except Exception:
		pass


_register_bpmn_data_fieldtype()
_patch_imported_data_fieldtypes()
_patch_db_type_map()
_patch_docfield_meta()
_patch_content_sanitizer()
_clear_bpmn_meta_caches()
