# Personal Experiments

Personal monorepo for experiments, research, and prototyping.

## Python Project Configurations

The root `pyproject.toml` defines the `personal-experiments` project and its dependencies for general work and notebooks. Its `[tool.uv.workspace]` section explicitly lists projects under `pyprojects`; currently, only `pyprojects/phdcalc` is listed. Adding a sibling directory alone does not register it as a workspace member.

Each member has its own `pyproject.toml` declaring its dependencies and build configuration. `phdcalc` currently uses setuptools with a `src/` layout; future projects can choose their own build configuration.

Workspace commands use the root `uv.lock` and, by default, the root `.venv`, including when invoked from a member directory. A member's local `uv.lock` or `.venv` is not selected automatically. All members must resolve together, even when installing only one. See [uv's workspace documentation](https://docs.astral.sh/uv/concepts/projects/workspaces/).

## Installation

Install `uv` and use Python 3.13 or later, as required by the current projects. Run the following commands from the repository root.

### Creating the Root Virtual Environment

```bash
uv sync
```

This creates or updates the root `.venv` with the root project's declared dependencies. It currently includes `phdcalc`, installed in editable mode because `[tool.uv.sources]` maps that dependency to the workspace member. It does not automatically install every future workspace member or each dependency's development tools.

For repository-level notebooks, select the root `.venv` interpreter (`.venv/Scripts/python.exe` on Windows or `.venv/bin/python` on Unix). Follow each project's README for any additional setup, such as API keys or external software.

### Working on an Individual Project

To install a registered workspace member and its dependencies, including its default `dev` group:

```bash
uv sync --package phdcalc
```

Use the member's `[project].name` for `--package`, which may differ from its directory name. Run tools with the same selection, for example:

```bash
uv run --package phdcalc ruff check pyprojects/phdcalc/src pyprojects/phdcalc/tests
```

This still uses the shared root `.venv`. Syncing is exact by default, so switching project selections can remove packages needed only by the previous selection. Use `uv sync` to restore the root selection, or install all workspace members and their default development groups together:

```bash
uv sync --all-packages
```

### Project-local Environments for Notebooks

Notebooks within an individual project can use that project's own virtual environment by selecting it as the notebook kernel. Notebooks in `pyprojects/phdcalc/notebooks` should use `pyprojects/phdcalc/.venv`.

From the repository root, create and populate that environment using the commands below. If the local `.venv` already exists, skip `uv venv` and start with activation.

**PowerShell**:

From the individual project directory (e.g., `pyprojects/phdcalc`), run:

```powershell
uv venv --python 3.13 .venv
```

Activate, sync and deactivate:

```powershell
.venv/Scripts/Activate.ps1
uv sync --active --package phdcalc
deactivate
```

**Git Bash on Windows**:

From the individual project directory (e.g., `pyprojects/phdcalc`), run:

```bash
uv venv --python 3.13 .venv
```

Activate, sync and deactivate:

```bash
source .venv/Scripts/activate
uv sync --active --package phdcalc
deactivate
```

**Bash on Linux or macOS**:

From the individual project directory (e.g., `pyprojects/phdcalc`), run:

```bash
uv venv --python .venv
```

Activate, sync and deactivate:

```bash
source .venv/bin/activate
uv sync --active --package phdcalc
deactivate
```

`--active` directs uv to the activated local environment; `--package` selects the member and its default development dependencies. Resolution still uses the repository-root `uv.lock`. Repeat the activation and sync steps when dependencies change.

In each notebook's kernel picker, select the Python interpreter at `pyprojects/phdcalc/.venv/Scripts/python.exe` on Windows or `pyprojects/phdcalc/.venv/bin/python` on Linux or macOS. In VS Code, use **Select Kernel > Python Environments**. Selecting the kernel is separate from activating an environment in a terminal; it also does not change uv's default environment for later shell commands.

For other projects, substitute their directory and `[project].name`, and ensure their dependencies include `ipykernel` for notebook use. `phdcalc` already includes it.

### Adding Another Project

Create an installable project with its own `pyproject.toml` under `pyprojects`. To make it a root dependency as well as a workspace member, run:

```bash
uv add ./pyprojects/example-project
```

Replace `example-project` with the new directory name. This registers the member, adds its package name to the root dependencies with a workspace source, updates the root `uv.lock`, and syncs the root environment. Later `uv sync` calls will include it.

If the project should be selectable independently without becoming a root dependency, add its directory to `[tool.uv.workspace].members` in the root `pyproject.toml`, then run:

```bash
uv lock
uv sync --package example-project
```

Here, replace `example-project` with the new package's `[project].name`. Keep the shared root lockfile updated when any member's dependencies change.
