## Wolfram Natural Language Calculator (WNLC) Interface Commands Help

WNLC provides an interface to use natural language to generate Wolfram Language code, evaluate it, and display the result in a Jupyter notebook.

The last successful calculation from `wc` or an evaluating `wnlc` pipeline is
available in the Wolfram session as `lhs` (the held input) and `rhs` (the
evaluated output). For example, `wc('rhs^2')` uses the previous output, while
`wc('ReleaseHold[lhs]')` evaluates the previous input again. The default and
`/calc` plot paths do not update these stored results. This means if you use a
prompt which generates a plot, the `lhs` and `rhs` variables will not be
updated.

In a natural-language `wnlc` prompt, use `!result` to operate on `rhs`, or
`!bothsides` to apply the same operation to both sides and display their
results as an equation. For example, `wnlc('Integrate !bothsides with respect
to x')`. After a two-sided calculation, the displayed left and right results
become the next held `lhs` and `rhs`. These references work in the default and
`/calc` pipelines, including when `/calc` has display options; `!result` also
works with `/code`. Write `!!result` or `!!bothsides` to include either token
literally.

Both references require a previous successful calculation. Using them together
raises `ValueError`; `!bothsides` also rejects `/code` and plot operations.
Reference expansion and literal escapes apply only to natural-language Wolfram
prompts, not `/run`, `/tex`, or `/help`. In `/run`, use Wolfram variable names
directly.

Add `/saveas !name` to an evaluating prompt to save its successful result in
the current Wolfram session. Refer to it as `!name` in later natural-language
prompts, or use `name` directly in Wolfram code:

```python
from pyderivehelper import wc, wnlc

wnlc('/calc Expand (x + 1)^2 /saveas !poly1 !expandedPoly')
wnlc('/calc Evaluate !poly1 at x = 2')
wnlc('/calc Differentiate !expandedPoly with respect to x')
wc('poly1 /. x -> 2')
```

Saved names are used directly as Wolfram variable names; `!` is only a prompt
marker. Both evaluation examples above produce `9`.

- Names must start with an ASCII letter and contain only ASCII letters and digits. Underscores are not allowed.
- Prefer lower camel case, such as `mySinIntegral` or `expandedPoly`.
- Names are case-sensitive. `result`, `bothsides`, `lhs`, and `rhs` are reserved.
- Avoid names that conflict with Wolfram built-in functions.

One `/saveas` command can save the same result under multiple names, separated
by spaces or tabs. Saved variables remain available as other calculations
change `!result`. Saving a name again overwrites that Wolfram variable.
`/saveas` requires a successful non-plot calculation and is unavailable with
`/code`, `/tex`, and `/help`. Use `!!name` to include a reference token
literally in a prompt.

Saved references work in the default, `/calc`, and `/code` prompts. An unknown
`!name` raises `ValueError`. With `!bothsides`, `/saveas` saves the right-hand
result. Names and results belong to the current session and are not restored
after restarting the notebook kernel.

Place pipeline commands and display options at the start of the prompt.
`/saveas` can appear elsewhere, as in the example above. If no command is
provided, the default pipeline is used. Multiple pipeline commands run in order
on the same prompt; `/showcode` and `/showtex` are options for `/calc` only. An
unknown leading command is logged and it and subsequent leading commands are
ignored; if no valid commands remain, the default pipeline runs.

The following pipelines are provided:

- `Default (no command)` generates Wolfram Language code, runs it, and shows the code, result, and rendered math.
- `/code` generates and validates Wolfram Language code, then displays only the code.
- `/tex` generates TeX but does not run anything.
- `/run` runs Wolfram Language code supplied directly.
- `/calc` generates and runs Wolfram Language code, then shows only the rendered equation.
- `/showcode` adds the generated Wolfram Language code to `/calc` output.
- `/showtex` adds the equation's TeX source to `/calc` output.
- `/help` shows this message.

Wolfram validation evaluates candidate code using `Check[..., $Failed]`; it is
not a syntax-only check. This applies to `/code` as well as the evaluating
pipelines, so validation can have side effects and code may run more than
once. `/code` starts the Wolfram kernel but skips the separate final
calculation and result display. `/tex` and `/help` do not start the kernel.
Package import still requires the API key environment variable specified in
`config.yaml`.

### Default Pipeline

Use the default pipeline to execute the full workflow from a plain-language
prompt.

The default pipeline generates Wolfram Language code, sanitizes and validates
it, shows the code, and then performs the final evaluation. If the code matches
a configured plot term, WNLC exports and displays a plot image. Otherwise, it
shows the raw result, the equation's TeX source, and the rendered equation. If
validation and repair fail, it shows the original generated code and skips
final evaluation.

### `/code` Pipeline

Use `/code` to display generated Wolfram Language code without a final result
display.

When the `/code` command prefaces a prompt, WNLC turns the plain-language
prompt into validated Wolfram Language code and displays the final code only.
Validation evaluates the code, but this pipeline does not save a new `lhs` or
`rhs` or render plot images. If validation and repair fail, WNLC shows the
original generated code instead.

### `/tex` Pipeline

Use `/tex` to generate TeX directly without converting to Wolfram Language or
evaluating anything.

When the `/tex` command prefaces a prompt, WNLC generates TeX through OpenAI,
checks whether `pylatexenc` can parse it, and displays the final TeX source
only. It does not compile or render the TeX or evaluate Wolfram code. If
validation and repair fail, WNLC shows the original generated TeX instead.

### `/run` Pipeline

Use `/run` for Wolfram Language code that should be checked and run.

When the `/run` command prefaces a prompt, WNLC sends supplied code to OpenAI
for sanitization, validates it, and requests repairs if needed. It shows the
final code, evaluates it, and displays the raw result, the equation's TeX
source, and the rendered equation. If validation and repair fail, WNLC shows
the original supplied code and skips final evaluation. Unlike the default and
`/calc` pipelines, `/run` has no plot-image export branch. Use `wc(expr)` for
direct evaluation without OpenAI sanitization or validation.

### `/calc` Pipeline

Use `/calc` for a compact answer from a plain-language prompt.

When the `/calc` command prefaces a prompt, WNLC generates, sanitizes, and
validates Wolfram Language code, then performs the final evaluation. For
ordinary results, it shows only the rendered input and result as an equation.
If the code matches a configured plot term, WNLC exports and displays the plot
image instead. If validation and repair fail, WNLC shows the original generated
code and skips final evaluation.

Combine `/calc` with `/showcode`, `/showtex`, or both to show the generated
Wolfram code or the equation's TeX source alongside the rendered result. For
example, `wnlc('/calc /showcode /showtex Integrate !result with respect to x')`.
The options may appear in any order and require `/calc`; they do not run
separate pipelines. For plots, `/showcode` shows the generated plot code,
while `/showtex` has no equation to show.

### `/help` Pipeline

Use `/help` to display this help message.

### Display and errors

For a single-variable indefinite integral, the ordinary equation display adds
`+ C` to the right-hand side. This is display formatting; the evaluated result
and any `/saveas` value do not include that added constant.

Kernel startup failures and OpenAI connection failures produce notebook
messages and return `None`. Invalid references, saved names, and display-option
combinations raise `ValueError`.

Successful non-plot calls in the default pipeline return `(result, result_tex)`.
Ordinary slash-command calls return `None`, while `!bothsides` calls return
`((left_result, right_result), equation_tex)`, including with `/calc`. Plot
paths return `None`.
