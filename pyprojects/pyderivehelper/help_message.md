## Wolfram Natural Language Calculator (WNLC) Interface Commands Help

WNLC provides an interface to use natural language to generate Wolfram Language code, evaluate it, and display the result in a Jupyter notebook.

Use commands of the form `/command` to choose what WNLC should return. If no command is provided, the default pipeline is used.

The following pipelines are provided:

- `Default (no command)` generates Wolfram Language code, runs it, and shows the code, result, and rendered math.
- `/code` generates Wolfram Language code but does not run it.
- `/tex` generates TeX but does not run anything.
- `/run` runs Wolfram Language code supplied directly.
- `/calc` generates and runs Wolfram Language code, then shows only the final rendered result.
- `/help` shows this message.

### Default Pipeline

Use the default pipeline to execute the full workflow from a plain-language prompt.

The default pipeline generates Wolfram Language code, checks it, shows the code, and then runs it. If the result is a plot, WNLC renders the plot image. Otherwise, it shows the raw result, the TeX form, and a rendered math view. If WNLC cannot repair invalid generated code, it shows the failed code instead of running it.

### `/code` Pipeline

Use `/code` to generate Wolfram Language code without running it.

When the `/code` command prefaces a prompt, WNLC turns the plain-language prompt into checked Wolfram Language code and displays the final code only. It does not evaluate the code or render plots. If the generated code cannot be repaired, WNLC shows the failed code instead.

### `/tex` Pipeline

Use `/tex` to generate TeX directly without converting to Wolfram Language or evaluating anything.

When the `/tex` command prefaces a prompt, WNLC turns a plain-language prompt into checked TeX and displays the final TeX only. It does not generate runnable Wolfram output or evaluate anything. If the generated TeX cannot be repaired, WNLC shows the failed TeX instead.

### `/run` Pipeline

Use `/run` for Wolfram Language code that should be checked and run.

When the `/run` command prefaces a prompt, WNLC validates supplied code, attempts simple repairs if needed, shows the final code, and then evaluates it. It displays the raw result, the TeX form, and a rendered math view. If the code cannot be repaired, WNLC shows the failed code instead of running it.

### `/calc` Pipeline

Use `/calc` for a compact answer from a plain-language prompt.

When the `/calc` command prefaces a prompt, WNLC generates and checks Wolfram Language code, then runs it. For ordinary results, it shows only the final rendered math. If the result is a plot, WNLC renders the plot image instead. If the generated code cannot be repaired, WNLC shows the failed code instead of running it.

### `/help` Pipeline

Use `/help` to display this help message.
