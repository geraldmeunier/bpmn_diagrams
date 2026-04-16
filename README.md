### BPMN Diagrams

Implementation inside Frappe of the [bpmn.io](https://github.com/bpmn-io/bpmn-js) javascrpit library.

That App adds a new fieldtype named BPMN to Frappe.

The fieldtype can be added to any doctype, allowing to draw a BPMN diagram.

Being not a developper, that app was fully developped through vibe coding.



### Installation

You can install this app using the [bench](https://github.com/frappe/bench) CLI:

```bash
cd $PATH_TO_YOUR_BENCH
bench get-app $URL_OF_THIS_REPO --branch version-16
bench install-app bpmn_diagrams
```

### Contributing

This app uses `pre-commit` for code formatting and linting. Please [install pre-commit](https://pre-commit.com/#installation) and enable it for this repository:

```bash
cd apps/bpmn_diagrams
pre-commit install
```

Pre-commit is configured to use the following tools for checking and formatting your code:

- ruff
- eslint
- prettier
- pyupgrade

### License

mit
