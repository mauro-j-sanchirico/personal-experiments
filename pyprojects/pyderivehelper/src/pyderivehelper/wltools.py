import logging
import os
import re
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any, cast

import matplotlib.image as mpimg
import matplotlib.pyplot as plt
import yaml
from dotenv import load_dotenv
from IPython.display import Markdown, Math, display
from openai import OpenAI
from wolframclient.evaluation import WolframLanguageSession
from wolframclient.language import wl

from pyderivehelper.openai_api import OpenAIModels, make_openai_api_call
from pyderivehelper.prompts import (
    SystemPrompts,
    populate_wolfram_code_generator_prompt_template,
    populate_wolfram_code_sanitizer_prompt_template,
    populate_wolfram_plot_summarizer_prompt_template,
)

_CONFIG_PATH: Path = Path(__file__).resolve().parents[2] / 'config.yaml'
logger = logging.getLogger(__name__)


def set_log_level(level: str) -> None:
    """Set this module's logger level.

    Args:
        level: Logging level name such as "INFO" or "DEBUG".
    """
    logger.setLevel(level.upper())


def _load_config() -> dict[str, str]:
    with _CONFIG_PATH.open(encoding='utf-8') as config_file:
        config: Any = yaml.safe_load(config_file)
    if not isinstance(config, dict):
        raise ValueError(f'Invalid config file: {_CONFIG_PATH}')
    return config


_CONFIG: dict[str, str] = _load_config()
_OPENAI_API_KEY_ENV_VAR: str = _CONFIG['openai_api_key_env_var']
_PLOT_DIRECTORY: str = _CONFIG['plot_directory']
_PLOT_EXTENSION: str = _CONFIG['plot_extension']
_RESULT_STR: str = _CONFIG['result_str']

# =============================================================================
# Session boiler plate to start Wolfram Language session and OpenAI client
# =============================================================================
load_dotenv()
ws: WolframLanguageSession = WolframLanguageSession()
_MATH_ASSISTANT_CLIENT: OpenAI = OpenAI(
    api_key=os.environ[_OPENAI_API_KEY_ENV_VAR]
)

# =============================================================================
# Wolfram Language configuration and constants
# =============================================================================

_WOLFRAM_LANGUAGE_FAILED_RESULT: str = 'False'


@dataclass
class SyntaxCheckResults:
    """Result markers used by syntax validation."""

    FAILED_RESULT: str = _WOLFRAM_LANGUAGE_FAILED_RESULT


# https://reference.wolfram.com/language/guide/DataVisualization.html
@dataclass
class PlotCommands:
    """Plot-related Wolfram Language command names."""

    commands: tuple[str, ...] = tuple(
        cast(list[str], _CONFIG['plot_commands'])
    )


# =============================================================================
# User convenience functions for displaying Wolfram Language results in Jupyter
# notebooks
# =============================================================================


def print_tex(expr: str) -> None:
    """Display a raw TeX expression.

    Args:
        expr: The TeX expression to render.
    """
    display(Math(expr))


def print_wexpr(expr: object) -> None:
    """Display a Wolfram expression as TeX.

    Args:
        expr: The Wolfram expression to render.
    """
    tex_expr: str = str(ws.evaluate(wl.ToString(wl.TeXForm(expr))))
    display(Math(tex_expr))


def print_wresult(expr: object) -> None:
    """Evaluate a Wolfram expression and display the result as Math via TeX.

    Args:
        expr: The Wolfram expression to evaluate.
    """
    tex_expr: str = str(
        ws.evaluate(wl.ToString(wl.TeXForm(ws.evaluate(expr))))
    )
    display(Math(tex_expr))


def print_wresult_tex(expr: object) -> None:
    """Evaluate a Wolfram expression and print the raw TeX result.

    Args:
        expr: The Wolfram expression to evaluate.
    """
    tex_expr: str = str(
        ws.evaluate(wl.ToString(wl.TeXForm(ws.evaluate(expr))))
    )
    logger.info(tex_expr)


# =============================================================================
# I/O validation functions
# =============================================================================


def check_syntax(expr: str) -> bool:
    """Check whether a Wolfram Language expression has valid syntax.

    Args:
        expr: The Wolfram Language expression to validate.

    Returns:
        True if the expression passes syntax validation, otherwise False.
    """
    valid_syntax_check_str: str = f'SyntaxQ["{expr}"]'
    syntax_check_result: str = str(ws.evaluate(valid_syntax_check_str))
    if SyntaxCheckResults.FAILED_RESULT in syntax_check_result:
        return False
    return True


def check_contains_plot_code(
    expr: str, plot_commands: tuple[str, ...] = PlotCommands.commands
) -> bool:
    """Check whether a Wolfram Language expression contains plot code.

    Args:
        expr: The Wolfram Language expression to inspect.
        plot_commands: Plot command names to search for.

    Returns:
        True if any plot command is found, otherwise False.
    """
    for command in plot_commands:
        if re.search(rf'{re.escape(command)}', expr):
            return True
    return False


# ============================================================================
# Main user-facing functions for generating and using Wolfram Language code
# ============================================================================


def wplot(filename: str, command: str) -> None:
    """Render a Wolfram Language plot from a saved image file.

    Args:
        filename: Path to the image file to display.
        command: Wolfram Language plot expression to export.
    """
    export_expr: str = f'Export["{filename}", {command}]'
    ws.evaluate(export_expr)
    img: object = mpimg.imread(filename)
    plt.figure()
    plt.imshow(img)
    plt.show()
    plt.axis('off')


def wc(expr: object) -> object:
    """Evaluate a Wolfram expression, store it, and print the result.

    The expression is stored in the Wolfram session under the symbol 'rrr' for
    easy access in subsequent Wolfram commands.

    Args:
        expr: The Wolfram expression to evaluate.

    Returns:
        The evaluated Wolfram result.
    """
    result: object = ws.evaluate(expr)
    save_expr_str: str = f'{_RESULT_STR} = {expr}'
    ws.evaluate(save_expr_str)
    print_wresult(ws.evaluate(_RESULT_STR))
    return result


def wnlc(
    prompt: str, model_str: str = OpenAIModels.mini
) -> tuple[object, str] | None:
    """Generate, validate, and evaluate Wolfram Language code.

    Args:
        prompt: Natural-language description of the desired computation.
        model_str: OpenAI model name used for code generation.

    Returns:
        The Wolfram result and cleaned TeX output, or None for plot or syntax
        cases.
    """
    logger.info('Generating Wolfram Language code...')
    response_str: str = _generate_wolfram_language(prompt, model_str)
    logger.info('Sanitizing generated code...')
    response_str: str = _sanitize_wolfram_language_code(
        response_str, OpenAIModels.mini
    )
    logger.info('Checking syntax...')
    if not check_syntax(response_str):
        _handle_syntax_error(response_str)
        return None
    _display_generated_code(response_str)
    logger.info('Checking for plot code...')
    if check_contains_plot_code(response_str):
        _generate_plot_from_wolfram_code(response_str)
        return None
    logger.info('Evaluating code...')
    result: object = ws.evaluate(response_str)
    cleaned_tex_str: str = _extract_clean_tex(result)
    _display_results(result, cleaned_tex_str)
    return result, cleaned_tex_str


# =============================================================================
# Wolfram code generation pipeline stages
# =============================================================================


def _generate_wolfram_language(prompt: str, model_str: str) -> str:
    """Generate Wolfram Language code from a prompt.

    Args:
        prompt: Natural-language prompt to convert.
        model_str: OpenAI model used for generation.

    Returns:
        Generated Wolfram Language code.
    """
    templated_prompt: str = populate_wolfram_code_generator_prompt_template(
        prompt
    )
    code: str = make_openai_api_call(
        _MATH_ASSISTANT_CLIENT,
        model_str,
        SystemPrompts.wolfram_code_generator,
        templated_prompt,
    )
    return code


def _sanitize_wolfram_language_code(code: str, model_str: str) -> str:
    """Sanitize Wolfram Language code with an OpenAI model.

    Args:
        code: Wolfram Language code to sanitize.
        model_str: OpenAI model used for sanitization.

    Returns:
        Sanitized Wolfram Language code.
    """
    templated_prompt: str = populate_wolfram_code_sanitizer_prompt_template(
        code
    )
    sanitized_code: str = make_openai_api_call(
        _MATH_ASSISTANT_CLIENT,
        model_str,
        SystemPrompts.wolfram_code_sanitizer,
        templated_prompt,
    )
    return sanitized_code


def _summarize_plot_code_to_filename(code: str, model_str: str) -> str:
    """Summarize plot code into a concise filename.

    Args:
        code: Wolfram Language plot code to summarize.
        model_str: OpenAI model used for summarization.

    Returns:
        A short snake_case filename stem.
    """
    templated_prompt: str = populate_wolfram_plot_summarizer_prompt_template(
        code
    )
    filename: str = make_openai_api_call(
        _MATH_ASSISTANT_CLIENT,
        model_str,
        SystemPrompts.wolfram_plot_summarizer,
        templated_prompt,
    )
    return filename


def _generate_plot_from_wolfram_code(response_str: str) -> None:
    """Render a plot generated from Wolfram Language code.

    Args:
        response_str: Wolfram Language plot code to render.
    """
    logger.info('Detected plot code. Rendering plot...')
    human_readable_filename: str = _summarize_plot_code_to_filename(
        response_str, OpenAIModels.mini
    )
    filename: str = _make_image_file(human_readable_filename)
    wplot(_to_relative_path(filename), response_str)


# =============================================================================
# Post processing and error handling
# =============================================================================


def _extract_clean_tex(result: object) -> str:
    """Convert a Wolfram result into cleaned TeX.

    Args:
        result: The Wolfram result to convert.

    Returns:
        Cleaned TeX text.
    """
    tex_str: str = str(ws.evaluate(wl.ToString(wl.TeXForm(result))))
    cleaned_tex_str: str = _fix_hypergeometric_functions(tex_str)
    return cleaned_tex_str


def _fix_hypergeometric_functions(tex_str: str) -> str:
    """Fix Wolfram's hypergeometric TeX output for notebook rendering.

    Args:
        tex_str: Raw TeX text from Wolfram.

    Returns:
        Adjusted TeX text.
    """
    cleaned_tex_str: str = re.sub(r' _(\d+[A-Za-z])', r' {}_\1', tex_str)
    return cleaned_tex_str


def _handle_syntax_error(response_str: str) -> None:
    """Display syntax validation output for invalid code.

    Args:
        response_str: Wolfram Language code that failed validation.
    """
    _display_syntax_error(response_str)


# =============================================================================
# Display functions
# =============================================================================


def _display_syntax_error(response_str: str) -> None:
    """Display an invalid-code message and the generated Wolfram code.

    Args:
        response_str: Wolfram Language code to show.
    """
    logger.info('Generated response is not valid Wolfram Language code.')
    display(Markdown('\n**Invalid Wolfram Code**:\n'))
    display(Markdown(f'```wolfram\n{response_str}\n```'))


def _display_generated_code(response_str: str) -> None:
    """Display generated Wolfram Language code.

    Args:
        response_str: Wolfram Language code to show.
    """
    display(Markdown('\n**Generated Wolfram Code**:\n'))
    display(Markdown(f'```wolfram\n{response_str}\n```'))


def _display_results(result: object, cleaned_tex_str: str) -> None:
    """Display the evaluated result and its TeX form.

    Args:
        result: The evaluated Wolfram result.
        cleaned_tex_str: Cleaned TeX text for the result.
    """
    display(Markdown('\n**Raw Evaluated Result**:\n'))
    display(Markdown(f'```plaintext\n{result!s}\n```'))
    display(Markdown('\n**Raw TeX**:\n'))
    display(Markdown(f'```tex\n{cleaned_tex_str}\n```'))
    display(Markdown('---'))
    display(Markdown('\n**Rendered Evaluated Result**:\n'))
    display(Markdown(f'$$\\Large {cleaned_tex_str}$$'))
    display(Markdown('---'))


# =============================================================================
# File handling and path manipulation functions
# =============================================================================


def _to_relative_path(filename: str) -> str:
    """Convert a filesystem path to a relative POSIX path.

    Args:
        filename: Absolute or local filesystem path.

    Returns:
        Relative path using forward slashes.
    """
    relative_path: str = os.path.relpath(filename, os.getcwd())
    return relative_path.replace('\\', '/')  # Handle Windows paths


def _make_image_file(human_readable_filename: str) -> str:
    """Create a plot image file path.

    Args:
        human_readable_filename: Prefix used for the temporary file name.

    Returns:
        Path to the created temporary image file.
    """
    prefix: str = human_readable_filename + '_'
    os.makedirs(_PLOT_DIRECTORY, exist_ok=True)
    with tempfile.NamedTemporaryFile(
        prefix=prefix,
        dir=_PLOT_DIRECTORY,
        suffix=_PLOT_EXTENSION,
        delete=False,
    ) as temp_file:
        filename: str = temp_file.name
        temp_file.close()  # Close the file so that Wolfram can write to it
    return filename
