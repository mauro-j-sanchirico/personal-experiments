import logging
import os
import re
import tempfile
from collections.abc import Callable
from dataclasses import dataclass
from typing import cast

from dotenv import load_dotenv
from IPython.display import Markdown, Math, display
from openai import OpenAI
from PIL import Image as PillowImage
from pylatexenc.latexwalker import LatexWalker
from wolframclient.evaluation import WolframLanguageSession
from wolframclient.language import wl, wlexpr

from pyderivehelper.agents import (
    TeXCodeFixer,
    TeXGenerator,
    WolframCodeFixer,
    WolframCodeGenerator,
    WolframCodeSanitizer,
    WolframPlotSummarizer,
)
from pyderivehelper.config_file_management import load_config
from pyderivehelper.openai_api import OpenAIModels

# =============================================================================
# Logger and config file setup
# =============================================================================

logger = logging.getLogger(__name__)


def set_log_level(level: str) -> None:
    """Set this module's logger level.

    Args:
        level: Logging level name such as "INFO" or "DEBUG".
    """
    logger.setLevel(level.upper())


_CONFIG: dict[str, str] = load_config()
_OPENAI_API_KEY_ENV_VAR: str = _CONFIG['openai_api_key_env_var']
_PLOT_DIRECTORY: str = _CONFIG['plot_directory']
_PLOT_EXTENSION: str = _CONFIG['plot_extension']
_RESULT_STR: str = _CONFIG['result_str']
_VALIDATION_RETRY_COUNT: int = max(
    0, int(_CONFIG['wolfram_code_validation_retry_count'])
)


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


# https://reference.wolfram.com/language/guide/DataVisualization.html
@dataclass(frozen=True)
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


def print_wresult_tex(expr: object) -> None:
    """Evaluate a Wolfram expression and print the raw TeX result.

    Args:
        expr: The Wolfram expression to evaluate.
    """
    tex_expr: str = str(
        ws.evaluate(wl.ToString(wl.TeXForm(ws.evaluate(expr))))
    )
    display(Markdown(f'```tex\n{tex_expr}\n```'))


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
    with PillowImage.open(filename) as img:
        display(img)


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
    clean_tex_expr: str = _extract_mathjax_safe_tex(ws.evaluate(_RESULT_STR))
    display(Math(clean_tex_expr))
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
    logger.info('Logger level: %s', logging.getLevelName(logger.level))
    prompt = _trim_leading_whitespace(prompt)
    slash_commands, prompt = _parse_slash_commands(prompt)
    if slash_commands:
        logger.info('Found slash command(s): %s', ', '.join(slash_commands))
        for command in slash_commands:
            slash_command_pipeline = _SLASH_COMMANDS[command]
            slash_command_pipeline(prompt, model_str)
    else:
        return _wnlc_default_pipeline(prompt, model_str)


# =============================================================================
# Pipelines
# =============================================================================


def _wnlc_code_pipeline(
    prompt: str, model_str: str
) -> tuple[object, str] | None:
    """Pipeline for the /code slash command."""
    logger.info('Executing /code pipeline...')
    validated_response_str, response_str = _generate_validated_wolfram_code(
        prompt, model_str
    )
    if not validated_response_str:
        _handle_wolfram_validation_error(response_str)
        return None
    _display_generated_code(validated_response_str)
    return (None, validated_response_str)


def _wnlc_tex_pipeline(
    prompt: str, model_str: str
) -> tuple[object, str] | None:
    """Pipeline for the /tex slash command."""
    logger.info('Executing /tex pipeline...')
    validated_response_str, response_str = _generate_validated_tex_code(
        prompt, model_str
    )
    if not validated_response_str:
        _handle_tex_validation_error(response_str)
        return None
    _display_generated_tex(validated_response_str)
    return (None, validated_response_str)


def _wnlc_run_pipeline(
    prompt: str, model_str: str
) -> tuple[object, str] | None:
    """Stub pipeline for the /run slash command."""
    logger.info('Executing /run pipeline...')


def _wnlc_report_pipeline(
    prompt: str, model_str: str
) -> tuple[object, str] | None:
    """Stub pipeline for the /report slash command."""
    logger.info('Executing /report pipeline...')


def _wnlc_help_pipeline(
    prompt: str, model_str: str
) -> tuple[object, str] | None:
    """Stub pipeline for the /help slash command."""
    logger.info('Executing /help pipeline...')


def _wnlc_default_pipeline(
    prompt: str, model_str: str
) -> tuple[object, str] | None:
    """Run the default Wolfram Language code-generation pipeline."""
    logger.info('Executing default pipeline...')
    validated_response_str, response_str = _generate_validated_wolfram_code(
        prompt, model_str
    )
    if not validated_response_str:
        _handle_wolfram_validation_error(response_str)
        return None
    _display_generated_code(validated_response_str)
    logger.info('Checking for plot code...')
    if check_contains_plot_code(validated_response_str):
        _generate_plot_from_wolfram_code(validated_response_str)
        return None
    logger.info('Evaluating code...')
    result: object = ws.evaluate(validated_response_str)
    cleaned_tex_str: str = _extract_mathjax_safe_tex(result)
    _default_display_results(result, cleaned_tex_str)
    return result, cleaned_tex_str


# =============================================================================
# Slash command configuration
# =============================================================================

_SlashCommandPipeline = Callable[[str, str], tuple[object, str] | None]

_SLASH_COMMANDS: dict[str, _SlashCommandPipeline] = {
    'code': _wnlc_code_pipeline,
    'tex': _wnlc_tex_pipeline,
    'run': _wnlc_run_pipeline,
    'report': _wnlc_report_pipeline,
    'help': _wnlc_help_pipeline,
}


# =============================================================================
# Pipeline steps
# =============================================================================


def _validate_or_fix_wolfram_code(
    candidate_code: str, wolfram_code_fixer: WolframCodeFixer
) -> str:
    """Validate Wolfram code and try to fix it if needed."""
    for _ in range(_VALIDATION_RETRY_COUNT + 1):
        if validate_wolfram_code(candidate_code):
            return candidate_code
        candidate_code = wolfram_code_fixer.call(candidate_code)
    return ''


def _validate_or_fix_tex_code(
    candidate_code: str, tex_code_fixer: TeXCodeFixer
) -> str:
    """Validate TeX code and try to regenerate it if needed."""
    for _ in range(_VALIDATION_RETRY_COUNT + 1):
        if validate_tex_code(candidate_code):
            return candidate_code
        candidate_code = tex_code_fixer.call(candidate_code)
    return ''


def _generate_validated_wolfram_code(
    prompt: str, model_str: str = OpenAIModels.mini
) -> tuple[str, str]:
    """Generate, sanitize, and validate Wolfram Language code."""
    wolfram_code_generator: WolframCodeGenerator = WolframCodeGenerator(
        _MATH_ASSISTANT_CLIENT, model_str
    )
    wolfram_code_sanitizer: WolframCodeSanitizer = WolframCodeSanitizer(
        _MATH_ASSISTANT_CLIENT, model_str
    )
    wolfram_code_fixer: WolframCodeFixer = WolframCodeFixer(
        _MATH_ASSISTANT_CLIENT, model_str
    )

    logger.info('Generating Wolfram Language code...')
    response_str: str = wolfram_code_generator.call(prompt)

    logger.info('Sanitizing generated code...')
    sanitized_response_str: str = wolfram_code_sanitizer.call(response_str)

    logger.info('Validating code...')
    validated_response_str: str = _validate_or_fix_wolfram_code(
        sanitized_response_str, wolfram_code_fixer
    )
    return validated_response_str, response_str


def _generate_validated_tex_code(
    prompt: str, model_str: str = OpenAIModels.mini
) -> tuple[str, str]:
    """Generate, sanitize, and validate TeX code."""
    tex_generator: TeXGenerator = TeXGenerator(
        _MATH_ASSISTANT_CLIENT, model_str
    )
    tex_code_fixer: TeXCodeFixer = TeXCodeFixer(
        _MATH_ASSISTANT_CLIENT, model_str
    )

    logger.info('Generating TeX code...')
    response_str: str = tex_generator.call(prompt)

    logger.info('Validating TeX code...')
    validated_response_str: str = _validate_or_fix_tex_code(
        response_str, tex_code_fixer
    )
    return validated_response_str, response_str


def _generate_plot_from_wolfram_code(response_str: str) -> None:
    """Render a plot generated from Wolfram Language code.

    Args:
        response_str: Wolfram Language plot code to render.
    """
    logger.info('Detected plot code. Rendering plot...')
    wolfram_plot_summarizer: WolframPlotSummarizer = WolframPlotSummarizer(
        _MATH_ASSISTANT_CLIENT, OpenAIModels.mini
    )
    human_readable_filename: str = wolfram_plot_summarizer.call(response_str)
    filename: str = _make_image_file(human_readable_filename)
    wplot(_to_relative_path(filename), response_str)


# =============================================================================
# I/O validation functions
# =============================================================================


def validate_wolfram_code(candidate_wolfram_code):
    result = ws.evaluate(wlexpr(f'Check[{candidate_wolfram_code}, $Failed]'))
    if result == wl.Symbol('$Failed'):
        return False
    return True


def validate_tex_code(latex_code: str) -> bool:
    """Return True when pylatexenc can parse the LaTeX code."""
    try:
        walker = LatexWalker(latex_code)
        walker.get_latex_nodes()
    except Exception:
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


# =============================================================================
# Post processing and error handling
# =============================================================================


def _extract_mathjax_safe_tex(result: object) -> str:
    """Convert a Wolfram result into cleaned TeX that will display in MathJax.

    Args:
        result: The Wolfram result to convert.

    Returns:
        Cleaned TeX text.
    """
    tex_str: str = str(ws.evaluate(wl.ToString(wl.TeXForm(result))))
    cleaned_tex_str: str = _fix_hypergeometric_functions(tex_str)
    cleaned_tex_str: str = _fix_fbox(cleaned_tex_str)
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


def _fix_fbox(tex_str: str) -> str:
    """Fix Wolfram boxed TeX output for notebook rendering.

    Args:
        tex_str: Raw TeX text from Wolfram.

    Returns:
        Adjusted TeX text with fbox removed.
    """
    cleaned_tex_str: str = re.sub(
        r'\\fbox\{\$(.*?)\$\}', r'\\boxed{\1}', tex_str
    )
    return cleaned_tex_str


def _handle_wolfram_validation_error(response_str: str) -> None:
    """Display validation output for code that could not be fixed."""
    logger.info('Generated response could not be validated.')
    display(Markdown('\n**Unfixable Wolfram Code**:\n'))
    display(Markdown(f'```wolfram\n{response_str}\n```'))


def _handle_tex_validation_error(response_str: str) -> None:
    """Display validation output for TeX that could not be fixed."""
    logger.info('Generated TeX could not be validated.')
    display(Markdown('\n**Unfixable TeX**:\n'))
    display(Markdown(f'```tex\n{response_str}\n```'))


# =============================================================================
# String utility functions
# =============================================================================

_LEADING_SLASH_TOKEN_PATTERN: re.Pattern[str] = re.compile(r'/([^\s/]+)')
_LEADING_SLASH_BLOCK_PATTERN: re.Pattern[str] = re.compile(
    r'^(?:/[^\s/]+(?:\s+|(?=/)|$))+'
)


def _trim_leading_whitespace(text: str) -> str:
    """Remove leading whitespace from text."""
    return text.lstrip()


def _parse_slash_commands(text: str) -> tuple[list[str], str]:
    """Validate leading slash commands and return the valid prefix.

    Args:
        text: Input text that may start with slash commands.

    Returns:
        A tuple of valid leading commands and the text with that valid prefix
        removed.
    """
    match: re.Match[str] | None = _LEADING_SLASH_BLOCK_PATTERN.match(text)
    if match is None:
        return [], text

    valid_commands: list[str] = []
    for command_match in _LEADING_SLASH_TOKEN_PATTERN.finditer(match.group(0)):
        command_name: str = command_match.group(1)
        if command_name not in _SLASH_COMMANDS:
            logger.error(
                'Unknown slash command /%s. Any subsequent slash commands '
                'were ignored.',
                command_name,
            )
            break
        valid_commands.append(command_name)

    return valid_commands, text[match.end() :].lstrip()


# =============================================================================
# Display functions
# =============================================================================


def _display_generated_code(response_str: str) -> None:
    """Display generated Wolfram Language code.

    Args:
        response_str: Wolfram Language code to show.
    """
    display(Markdown('\n**Generated Wolfram Code**:\n'))
    display(Markdown(f'```wolfram\n{response_str}\n```'))


def _display_generated_tex(response_str: str) -> None:
    """Display generated TeX code."""
    display(Markdown('\n**Generated TeX**:\n'))
    display(Markdown(f'```tex\n{response_str}\n```'))


def _default_display_results(result: object, cleaned_tex_str: str) -> None:
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
