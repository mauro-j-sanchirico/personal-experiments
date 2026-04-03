from dataclasses import dataclass
from typing import Any

from pyderivehelper.config_file_management import load_config

_CONFIG: dict[str, Any] = load_config()


@dataclass(frozen=True)
class SystemPrompts:
    wolfram_code_generator: str = _CONFIG[
        'wolfram_code_generator_system_prompt'
    ]
    wolfram_code_sanitizer: str = _CONFIG[
        'wolfram_code_sanitizer_system_prompt'
    ]
    wolfram_plot_summarizer: str = _CONFIG[
        'wolfram_plot_summarizer_system_prompt'
    ]


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
