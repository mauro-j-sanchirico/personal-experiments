# Personal Experiments

Personal monorepo for experiments, research, and prototyping.

## Python Project Configurations

The root `pyproject.toml` defines the top-level (`personal-experiments`) project and its dependencies for general work and notebooks. Its `[tool.uv.workspace]` section includes addition specific projects built in the `pyprojects` folder (e.g., `pyprojects/pyderivehelper`). `[tool.uv.sources]` tells uv to use that local project for the `pyderivehelper` dependency.

For each Python package in `pyprojects`, `pyprojects/*/pyproject.toml` defines the specific package's own dependencies and its setuptools build from `src/`. The root `uv.lock` resolves the workspace together. Run `uv sync` from the repository root to update the
root `.venv` and install `pyderivehelper` in editable mode. Select that `.venv` as the kernel for notebooks under the top level project.

## Installation

### Creating the Root Virtual Environment

The root project contains a virtual environment that can be used for general work. Subprojects can have their own virtual environments or be installed into the main virtual environment.

To sync the root `uv` environment:

```bash
uv sync
```

### Installing Sub-projects

Each installable project under `pyprojects` has its own `pyproject.toml`.

To add a new project to the root environment, run this from the repository root:

```sh
uv add ./pyprojects/$PROJECT_NAME
```

This adds the project as a workspace member and a root dependency, updates the root `uv.lock`, and installs it in editable mode in the root `.venv`. For an existing checkout, `uv sync` installs all declared root dependencies.
