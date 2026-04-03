from dataclasses import dataclass
from typing import Any

from pyderivehelper.config_file_management import load_config
from pyderivehelper.openai_api import make_openai_api_call

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
    def __init__(self, client: object, model: str, system_prompt: str) -> None:
        self.client = client
        self.model = model
        self.system_prompt = system_prompt

    def template_prompt(self, prompt: str) -> str:
        raise NotImplementedError

    def call(self, prompt: str) -> str:
        """Template a prompt and send it to the OpenAI API."""
        templated_prompt: str = self.template_prompt(prompt)
        response: str = make_openai_api_call(
            self.client,
            self.model,
            self.system_prompt,
            templated_prompt,
        )
        return response


class WolframCodeGenerator(Agent):
    def __init__(self, client: object, model: str) -> None:
        super().__init__(client, model, SystemPrompts.wolfram_code_generator)

    def template_prompt(self, prompt: str) -> str:
        return f"""
    Convert the following description into a Wolfram Language expression.
    Description:
    {prompt}
    Wolfram Language:
    """


class WolframCodeSanitizer(Agent):
    def __init__(self, client: object, model: str) -> None:
        super().__init__(client, model, SystemPrompts.wolfram_code_sanitizer)

    def template_prompt(self, code: str) -> str:
        return f"""
    The following Wolfram Language code may contain syntax errors or other
    issues. Correct it to ensure it can be evaluated in a Wolfram kernel.
    Code:
    {code}
    Sanitized Code:
    """


class WolframPlotSummarizer(Agent):
    def __init__(self, client: object, model: str) -> None:
        super().__init__(client, model, SystemPrompts.wolfram_plot_summarizer)

    def template_prompt(self, code: str) -> str:
        return f"""
    Analyze the following Wolfram Language code that generates a plot and
    provide a concise filename with no spaces that describes the plot.
    Code:
    {code}
    Filename:
    """
