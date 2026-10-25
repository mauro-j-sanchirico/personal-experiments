# PyDeriveHelper

`pyderivehelper` is a set of Python tools for performing mathematical
calculations using Wolfram Language in a Jupyter notebook. Interfaces are
provided for entering Wolfram Code directly and via natural language
descriptions through OpenAI API calls.

## Description

The `pyderivehelper` notebook interface provides two main functions:

- `wc(expr)` evaluates Wolfram Language directly, displays the raw result and
  an equation in TeX and rendered form, and returns the evaluated result.
- `wnlc(prompt, model_str=...)` uses OpenAI's API to generate and check Wolfram
  Language or TeX. Commands select code output, calculation output, or plots.

Calculations share a Wolfram session, so later prompts can reuse the previous
input and result or named results.

A number of pipelines are provided (see `help_message.md`) which can be invoked
with commands of the form `/<pipeline>`. The default and `/calc` pipelines
support exporting recognized plot expressions as images and display them in the notebook

## Dependencies

### Python and notebook environment

Python 3.13 or later and `uv` are required for the installation workflow below.
Use a Jupyter-compatible notebook frontend, such as VS Code's notebook editor.
The project installs `ipykernel` and its Python dependencies through `uv sync`.
PowerShell or bash can be used; no shell extensions are required.

### Wolfram Engine

An installed, activated [Wolfram Engine](https://www.wolfram.com/engine/) that
`wolframclient` can discover is required for Wolfram calculations, including
`/code` validation. The project does not specify a minimum Engine version.

If Wolfram Engine is already installed, the current version can be checked via
bash.

```bash
wolframscript -code '$VersionNumber'
```

Activate the Engine with a license appropriate to your use case; see the
[license FAQ](https://www.wolfram.com/engine/faq/).

### OpenAI

An OpenAI API key is required by the current package initialization, even when
using only `wc` or `/help`. The key's environment variable name is configured
in `config.yaml`; its default is `OPENAI_PERSONAL_MATH_ASSISTANT`.

`wnlc` defaults to `gpt-5.4-mini`, as defined in `openai_api.py`. Pass
`model_str` to select a different model for generation, sanitization, and
repair. Plot filenames always use `OpenAIModels.mini`, regardless of
`model_str`.

## Installation

From this directory, run `uv sync`. This installs `pyderivehelper` in `.venv`.

Before importing the package, set `OPENAI_PERSONAL_MATH_ASSISTANT` in your
environment or add a `.env` file in this project directory:

```dotenv
OPENAI_PERSONAL_MATH_ASSISTANT=your-api-key
```

The package loads `.env` on import. `.env` is ignored by Git.

In the notebook, select this project's `.venv` Python interpreter as the kernel
(`.venv/Scripts/python.exe` on Windows or `.venv/bin/python` on Unix).

### Configuration

The source checkout's `config.yaml` contains the API key environment variable
name, agent prompts, plot detection terms, plot output settings, and validation
retry count. Settings are loaded at import time; restart the notebook kernel
after changing them.

Plots default to `.png` files in `images/`, relative to the notebook process's
working directory. Generated files remain on disk. Keep `config.yaml` and
`help_message.md` in the project directory: the current implementation reads
them from the source checkout.

## Testing

From this directory, run the test suite with:

```bash
uv run pytest
```

To run with coverage report, use

```bash
uv run pytest --cov=pyderivehelper
```

or

```bash
uv run pytest --cov=pyderivehelper --cov-report=term-missing tests
```

to report uncovered lines.

The suite tests command routing, result references, validation and repair,
formatting, plot file handling, configuration, and error reporting. It mocks
Wolfram kernel startup and external calls, and supplies a placeholder API key
when none is set. It does not verify live OpenAI responses or Wolfram Engine
calculations.

### Linting and type checking

From this directory, run Ruff for lint checks and mypy for static type checks:

```bash
uv run ruff check src tests
uv run mypy src tests
```

Both tools are included in the development dependencies installed by `uv sync`.
Ruff uses the repository's `ruff.toml`.

## Usage

```python
from pyderivehelper import wc, wnlc

wc('Expand[(x + 1)^2]')
wnlc('Integrate x^2 with respect to x')
wnlc('/calc /showcode /showtex Differentiate Sin[x] with respect to x')
wnlc('/code Solve x^2 = 4 for x')
wnlc('/tex The quadratic formula')
wnlc('/run Integrate[x^2, x]')
wnlc('/calc Plot Sin[x] for x from 0 to 2 Pi')
wnlc('/help')
```

`wc` evaluates directly without an OpenAI call. `/run` sends supplied code to
OpenAI for sanitization before validation and evaluation. Wolfram validation
evaluates candidate code using `Check[..., $Failed]`, including in `/code`;
it is not a syntax-only check and can have side effects. `/code` displays code
without a separate final calculation or result display. `/tex` and `/help`
do not start the Wolfram kernel.

### Reusing results

The last successful calculation is stored as `lhs` (held input) and `rhs`
(evaluated output). Use `wc('rhs^2')` to square the previous output, or
`wc('ReleaseHold[lhs]')` to evaluate the previous input again. In a default or
`/calc` prompt, `!result` refers to the previous output and `!bothsides`
applies the requested operation to both sides of the previous equation.
`!result` also works with `/code`. These references require a previous
successful calculation and cannot be combined in one prompt. `!bothsides`
does not support `/code` or plot operations.

Use `/saveas !name` to save a calculation's result in the current Wolfram
session. Refer to it as `!name` in later natural-language prompts, or use
`name` directly in Wolfram code:

```python
from pyderivehelper import wc, wnlc

wnlc('/calc Expand (x + 1)^2 /saveas !poly1 !expandedPoly')
wnlc('/calc Evaluate !poly1 at x = 2')
wnlc('/calc Differentiate !expandedPoly with respect to x')
wc('poly1 /. x -> 2')
```

Saved names are used directly as Wolfram variable names; `!` is only a prompt
marker. Both evaluation examples above produce `9`.

- Names must start with an ASCII letter and contain only ASCII letters and
  digits. Underscores are not allowed.
- Names are case-sensitive. `result`, `bothsides`, `lhs`, and `rhs` are reserved.
- Avoid using names that conflict with Wolfram built-in functions.

One `/saveas` command can save the same result under multiple names, separated
by spaces or tabs. Saved variables remain available as other calculations
change `!result`. Saving a name again overwrites that Wolfram variable.
Use `!!name` to include a reference token literally in a prompt.

`/saveas` requires a successful non-plot calculation and is unavailable with
`/code`, `/tex`, and `/help`. See [the command reference](help_message.md) or
run `wnlc('/help')` for all commands.

### Return values and logging

`wc` returns the evaluated result. For successful non-plot calculations,
`wnlc` in the default pipeline returns `(result, result_tex)`. Ordinary
slash-command calls return `None`; a `!bothsides` calculation returns
`((left_result, right_result), equation_tex)`, including with `/calc`.
Plots, kernel startup failures, and handled OpenAI connection failures return
`None`. Use the displayed output and saved Wolfram variables when working
with slash commands.

To show diagnostic logs:

```python
from pyderivehelper import set_log_level

set_log_level('DEBUG')
```

## License

This project is provided with an MIT license (see `LICENSE` file). Additional dependencies have their own licenses which might apply depending on use case.

### Wolfram Engine

For Wolfram Engine, see the [license FAQ](https://www.wolfram.com/engine/faq/).

## Contributing

Please email Mauro Sanchirico sanchirico.mauro@gmail.com with questions, comments, bug reports, or suggestions for improvement.
