# Personal Experiments

Personal monorepo for experiments, research, and prototyping.

## Installation

### Creating the Root Virtual Environment

The root project contains a virtual environment that can be used for general work. Subprojects can have their own virtual environments or be installed into the main virtual environment.

To initialize the root virtual environment:

```bash
uv init
```

### Installing Sub-projects

Any subfolder under the `pyprojects` folder is a standalone project and meant to be installed.

To install a project under `pyprojects` execute the following from the project root.

```bash
uv pip install -e pyprojects/$PROJECT_NAME
```
