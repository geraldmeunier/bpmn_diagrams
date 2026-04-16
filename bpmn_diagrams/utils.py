def before_request():
	# Force the app package import in web request workers so the BPMN runtime
	# registration in bpmn_diagrams.__init__ is applied before document save.
	import bpmn_diagrams  # noqa: F401
