# Personal Experiments

Personal monorepo for experiments, research, and prototyping.

## Memos

A number of memos and technical notes on topics of interest are hosted here.

- [Hamming's Proof of Noise Growth Under Application of the Discrete Derivative](https://mauro-j-sanchirico.github.io/personal-experiments/memos/discrete_derivatives/discrete_derivatives.pdf)
- [Building Intuition for the Pseudoinverse and SVD via Optimization](https://mauro-j-sanchirico.github.io/personal-experiments/memos/pseudoinverse_and_svd/pseudoinverse_and_svd.pdf)
- [Example Markdown](https://mauro-j-sanchirico.github.io/personal-experiments/memos/example_memo_markdown/example_memo_markdown.pdf)
- [Example notebook](https://mauro-j-sanchirico.github.io/personal-experiments/memos/example_memo_notebook/example_memo_notebook.pdf)

## Python Project Configurations

The root `pyproject.toml` defines the `personal-experiments` project and its dependencies for general work and notebooks. Its `[tool.uv.workspace]` section explicitly lists projects under `pyprojects`; currently, only `pyprojects/phdcalc` is listed. Adding a sibling directory alone does not register it as a workspace member.

Each member has its own `pyproject.toml` declaring its dependencies and build configuration. `phdcalc` currently uses setuptools with a `src/` layout; future projects can choose their own build configuration.

Workspace commands use the root `uv.lock` and, by default, the root `.venv`, including when invoked from a member directory. A member's local `uv.lock` or `.venv` is not selected automatically. All members must resolve together, even when installing only one. See [uv's workspace documentation](https://docs.astral.sh/uv/concepts/projects/workspaces/).

## Installation

Install `uv` and use Python 3.13 or later, as required by the current projects. Run the following commands from the repository root.

### Memo Publication Dependencies

The memos area in this repository is a common location for technical memos and notes, which can be built as PDFs in a common format from either markdowns or notebooks.

Generating memo PDFs requires Bash, standard Unix utilities (`sed`, `mktemp`, and `rm`), [Pandoc](https://pandoc.org/installing.html) for converting notebooks and markdown documents to a common PDF format, and a LaTeX distribution with XeLaTeX, the `etoolbox` package, and Latin Modern fonts. On Windows, Git Bash provides Bash and the Unix utilities. Install a LaTeX distribution such as [TeX Live](https://tug.org/texlive/).

[pandoc-crossref](https://github.com/lierdakil/pandoc-crossref) is required for equation numbering and cross-referencing. Download the archive for the required platform from its [releases page](https://github.com/lierdakil/pandoc-crossref/releases), extract it, and put the `pandoc-crossref` executable in a directory on your `PATH`.

On Windows, the release archive is a `.7z` file. Extract it with a tool such as [7-Zip](https://www.7-zip.org/). Per the release note, choose a release built against the same Pandoc version you have installed. For example, pandoc-crossref release `v0.3.26a` was built against Pandoc `3.13`.

Open a new terminal and check the installed versions and XeLaTeX:

```bash
pandoc --version
pandoc-crossref --version
xelatex --version
```

To build the existing memos locally, run `bash memos/make-pdfs.sh` from the repository root.

The GitHub Pages workflow installs `pandoc`, `pandoc-crossref`, `texlive-xetex`, `texlive-latex-extra`, and `fonts-lmodern` on Ubuntu to build the PDFs remotely.

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

## Usage

### Writing Technical Notes in the `memos` Area

The `memos` area of this repository is intended to hold technical notes and educational references on various topics of interest. Follow the steps below to add technical notes to the `memos` area.

1. Create a directory under `memos` for the note, and add a Markdown file or Jupyter notebook. Use the [Markdown example](memos/example_memo_markdown/example_memo_markdown.md) or [notebook example](memos/example_memo_notebook/example_memo_notebook.ipynb) as a starting point.
2. Add the source path relative to `memos` under `pdfs:` in [pdfs.yaml](memos/pdfs.yaml), for example `- my_memo/my_memo.md`.
3. Build the PDF from the repository root with `bash memos/make-pdfs.sh my_memo`. Omit the directory name to build all registered memos. Add a link to the published PDF in the Memos list above if it should be listed there.

Start the source with a `# Title`, followed by the bold `Authors:`, `Published:`, `Copyright Year:`, and `Copyright Name:` fields shown in the examples. Write the abstract as `**Abstract**: ...`. In a notebook, put the title, fields, and bibliography metadata in the first Markdown cell; use additional Markdown and code cells for the body. Save the notebook with the outputs you want in the PDF.

Use `##` for sections and `###` for subsections. The PDF builder promotes these headings to numbered sections and subsections and generates a table of contents. Use `## References` and, optionally, `## Appendix` for the special unnumbered headings shown in the examples.

Label a displayed equation and refer to it by its label:

```markdown
The mean is given by @eq:mean.

$$
\bar{x} = \frac{x_1 + x_2}{2}
$$ {#eq:mean}
```

For references, place a `references.bib` BibTeX file in the memo directory and declare it in a YAML metadata block (`---`, `bibliography: references.bib`, `---`). In Markdown, put this block at the beginning of the file; in a notebook, follow the placement in the first cell of the example. Cite an entry by its BibTeX key, such as `@abramowitz1964`, and place the following under `## References` where the bibliography should appear:

```markdown
::: {#refs}
:::
```
