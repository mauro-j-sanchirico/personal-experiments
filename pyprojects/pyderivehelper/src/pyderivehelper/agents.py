"""Build Wolfram and TeX prompts using system prompts loaded at import time."""

import logging
from dataclasses import dataclass
from typing import Any

from pyderivehelper.config_file_management import load_config
from pyderivehelper.openai_api import make_openai_api_call

logger = logging.getLogger(__name__)

_CONFIG: dict[str, Any] = load_config()


@dataclass(frozen=True)
class SystemPrompts:
    """Agent system prompts read from the project configuration."""

    tex_generator: str = _CONFIG['tex_generator_system_prompt']
    tex_code_fixer: str = _CONFIG['tex_code_fixer_system_prompt']
    wolfram_code_generator: str = _CONFIG[
        'wolfram_code_generator_system_prompt'
    ]
    wolfram_code_sanitizer: str = _CONFIG[
        'wolfram_code_sanitizer_system_prompt'
    ]
    wolfram_plot_summarizer: str = _CONFIG[
        'wolfram_plot_summarizer_system_prompt'
    ]
    wolfram_code_fixer: str = _CONFIG['wolfram_code_fixer_system_prompt']


class Agent:
    """Share API-call behavior across agents with specialized prompt templates."""

    def __init__(self, client: object, model: str, system_prompt: str) -> None:
        """Store the client, model, and system prompt for subsequent calls."""
        self.client = client
        self.model = model
        self.system_prompt = system_prompt

    def template_prompt(self, prompt: str) -> str:
        """Require subclasses to implement the user-prompt template."""
        raise NotImplementedError

    def call(self, prompt: str) -> str:
        """Template a prompt and send it to the OpenAI API."""
        templated_prompt: str = self.template_prompt(prompt)
        logger.debug('%s templated prompt: %r', type(self).__name__, templated_prompt)
        response: str = make_openai_api_call(
            self.client,
            self.model,
            self.system_prompt,
            templated_prompt,
        )
        logger.debug('%s response: %r', type(self).__name__, response)
        return response


class WolframCodeGenerator(Agent):
    """Request Wolfram Language code from natural-language descriptions."""

    def __init__(self, client: object, model: str) -> None:
        """Initialize the agent with the configured Wolfram generation prompt."""
        super().__init__(client, model, SystemPrompts.wolfram_code_generator)

    def template_prompt(self, prompt: str) -> str:
        """Format a description as a request for a Wolfram Language expression."""
        return f"""
    Convert the following description into a Wolfram Language expression.
    Description:
    {prompt}
    Wolfram Language:
    """


class WolframCodeSanitizer(Agent):
    """Request corrections to Wolfram Language code before validation."""

    def __init__(self, client: object, model: str) -> None:
        """Initialize the agent with the configured Wolfram sanitizer prompt."""
        super().__init__(client, model, SystemPrompts.wolfram_code_sanitizer)

    def template_prompt(self, code: str) -> str:
        """Format Wolfram code as a request to correct syntax and other issues."""
        return f"""
    The following Wolfram Language code may contain syntax errors or other
    issues. Correct it to ensure it can be evaluated in a Wolfram kernel.
    Code:
    {code}
    Sanitized Code:
    """


class WolframCodeFixer(Agent):
    """Request repairs to Wolfram Language code that failed evaluation."""

    def __init__(self, client: object, model: str) -> None:
        """Initialize the agent with the configured Wolfram repair prompt."""
        super().__init__(client, model, SystemPrompts.wolfram_code_fixer)

    def template_prompt(self, code: str) -> str:
        """Format failed Wolfram code as a repair request."""
        return f"""
    The following Wolfram Language code produced an error during evaluation.
    Analyze the error and fix the code to ensure it can be evaluated in a
    Wolfram kernel.
    Code:
    {code}
    Fixed Code:
    """


class WolframPlotSummarizer(Agent):
    """Request descriptive filenames for Wolfram Language plots."""

    def __init__(self, client: object, model: str) -> None:
        """Initialize the agent with the configured plot summarization prompt."""
        super().__init__(client, model, SystemPrompts.wolfram_plot_summarizer)

    def template_prompt(self, code: str) -> str:
        """Format plot code as a request for a concise filename without spaces."""
        return f"""
    Analyze the following Wolfram Language code that generates a plot and
    provide a concise filename with no spaces that describes the plot.
    Code:
    {code}
    Filename:
    """


class TeXGenerator(Agent):
    """Request TeX source from natural-language descriptions."""

    def __init__(self, client: object, model: str) -> None:
        """Initialize the agent with the configured TeX generation prompt."""
        super().__init__(client, model, SystemPrompts.tex_generator)

    def template_prompt(self, prompt: str) -> str:
        """Format a description as a request for TeX source."""
        return f"""
    Convert the following description into TeX code.
    Description:
    {prompt}
    TeX:
    """


class TeXCodeFixer(Agent):
    """Request repairs to TeX source that failed validation."""

    def __init__(self, client: object, model: str) -> None:
        """Initialize the agent with the configured TeX repair prompt."""
        super().__init__(client, model, SystemPrompts.tex_code_fixer)

    def template_prompt(self, code: str) -> str:
        """Format invalid TeX source as a repair request."""
        return f"""
    The following TeX code produced an error during validation.
    Analyze the error and fix the code so it is valid TeX.
    Code:
    {code}
    Fixed Code:
    """
