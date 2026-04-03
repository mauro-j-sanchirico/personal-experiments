from dataclasses import dataclass

_WOLFRAM_CODE_GENERATOR_SYSTEM_PROMPT = """
You are a Wolfram Language code generator.

Your task is to translate natural language descriptions of mathematical
operations into executable Wolfram Language code.

Strict requirements:
- Output ONLY Wolfram Language code.
- No explanations.
- No comments.
- No markdown.
- No surrounding text.
- When a substitution is requested, use ReplaceAll with the syntax expr /. var -> value.
- Ensure the result can be evaluated directly in a Wolfram kernel.
- Do as much with Wolfram Language as possible and avoid doing math in the
  natural language stage of the pipeline.
- Return exactly one valid Wolfram Language expression.
"""

_WOLFRAM_CODE_SANITIZER_SYSTEM_PROMPT = """
You are a Wolfram Language code sanitizer.

Your task is to take Wolfram Language code that may contain syntax or other
errors and correct it. Pay special attention to errors that are syntactically
correct but would cause other unexpected issues.

Pay special attention to the following while sanitizing:
- IMPORTANT: For any plotting expressions, ensure each inner expression to be
  plotted is wrapped in an Evaluate@ call to ensure proper plotting.
- Wrap expressions in FullSimplify as the outermost function UNLESS it is a
  plotting expression.
- Fix any syntax errors in the code to ensure it can be evaluated in a Wolfram
  kernel.
- Make no other modifications to the code beyond what is necessary for
  sanitization.
"""

_WOLFRAM_PLOT_SUMMARIZER_SYSTEM_PROMPT = """
You are a Wolfram Language plot summarizer.
Your task is to analyze Wolfram Language code that generates a plot and provide
a concise filename with no spaces that describes the plot.

Strict requirements:
- Always use snake_case for the filename.
- Do not include the file extension in the filename.
- NEVER include spaces or special characters in the filename.
"""


@dataclass(frozen=True)
class SystemPrompts:
    wolfram_code_generator: str = _WOLFRAM_CODE_GENERATOR_SYSTEM_PROMPT
    wolfram_code_sanitizer: str = _WOLFRAM_CODE_SANITIZER_SYSTEM_PROMPT
    wolfram_plot_summarizer: str = _WOLFRAM_PLOT_SUMMARIZER_SYSTEM_PROMPT


class Agent:
    def __init__(self, system_prompt: str, model: str) -> None:
        self.system_prompt = system_prompt
        self.model = model

    def template_prompt(self, prompt: str) -> str:
        raise NotImplementedError


class WolframCodeGenerator(Agent):
    def __init__(self, model: str) -> None:
        super().__init__(SystemPrompts.wolfram_code_generator, model)

    def template_prompt(self, prompt: str) -> str:
        return f"""
    Convert the following description into a Wolfram Language expression.
    Description:
    {prompt}
    Wolfram Language:
    """


class WolframCodeSanitizer(Agent):
    def __init__(self, model: str) -> None:
        super().__init__(SystemPrompts.wolfram_code_sanitizer, model)

    def template_prompt(self, code: str) -> str:
        return f"""
    The following Wolfram Language code may contain syntax errors or other
    issues. Correct it to ensure it can be evaluated in a Wolfram kernel.
    Code:
    {code}
    Sanitized Code:
    """


class WolframPlotSummarizer(Agent):
    def __init__(self, model: str) -> None:
        super().__init__(SystemPrompts.wolfram_plot_summarizer, model)

    def template_prompt(self, code: str) -> str:
        return f"""
    Analyze the following Wolfram Language code that generates a plot and
    provide a concise filename with no spaces that describes the plot.
    Code:
    {code}
    Filename:
    """
