from pathlib import Path


def after_install():
	ensure_bpmn_assets_link()


def ensure_bpmn_assets_link():
	app_root = Path(__file__).resolve().parent.parent
	vendor_dir = app_root / "bpmn_diagrams" / "public" / "vendor"
	link_path = vendor_dir / "bpmn-js"
	target = Path("../../../node_modules/bpmn-js/dist/assets")

	vendor_dir.mkdir(parents=True, exist_ok=True)

	if link_path.is_symlink() or link_path.exists():
		link_path.unlink()

	link_path.symlink_to(target)
