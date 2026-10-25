import logging
import os
import re
import tempfile
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import cast

from dotenv import load_dotenv
from IPython.display import Markdown, Math, display
from openai import APIConnectionError, OpenAI
from PIL import Image as PillowImage
from pylatexenc.latexwalker import LatexWalker
from wolframclient.evaluation import WolframLanguageSession
from wolframclient.exception import WolframKernelException
from wolframclient.language import wl, wlexpr
from wolframclient.language.expression import WLSymbol

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
    logging.getLogger('pyderivehelper.agents').setLevel(level.upper())


_CONFIG: dict[str, str] = load_config()
_OPENAI_API_KEY_ENV_VAR: str = _CONFIG['openai_api_key_env_var']
_PLOT_DIRECTORY: str = _CONFIG['plot_directory']
_PLOT_EXTENSION: str = _CONFIG['plot_extension']
_VALIDATION_RETRY_COUNT: int = max(
    0, int(_CONFIG['wolfram_code_validation_retry_count'])
)
_HELP_MESSAGE_PATH: Path = Path(__file__).resolve().parents[2] / 'help_message.md'


# =============================================================================
# Session boiler plate to start Wolfram Language session and OpenAI client
# =============================================================================


load_dotenv()
ws: WolframLanguageSession = WolframLanguageSession()
_LAST_RESULT_AVAILABLE = False
_SAVED_RESULT_NAMES: set[str] = set()
_NO_LEFT_RESULT = object()
_MATH_ASSISTANT_CLIENT: OpenAI = OpenAI(
    api_key=os.environ[_OPENAI_API_KEY_ENV_VAR]
)


def _start_wolfram_session() -> bool:
    """Start the kernel and report startup failures in the notebook."""
    try:
        ws.start()
    except WolframKernelException:
        logger.debug('Wolfram kernel startup failed', exc_info=True)
        display(Markdown(
            '**Wolfram Engine could not start.** Your license may already '
            'be using all available kernel sessions. Shut down an unused '
            'Jupyter kernel and try again. If this persists, check your '
            'Wolfram Engine license or installation.'
        ))
        return False
    return True


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

    The input is stored as held `lhs`; its evaluated value is stored as `rhs`.

    Args:
        expr: The Wolfram expression to evaluate.

    Returns:
        The evaluated Wolfram result, or None if the kernel cannot start.
    """
    if not _start_wolfram_session():
        return None
    result: object = _evaluate_and_remember(str(expr))
    cleaned_tex_str: str = _extract_mathjax_safe_tex(result)
    equation_tex_str: str = _build_equation_tex(cleaned_tex_str)
    _default_display_results(result, equation_tex_str)
    return result


def wnlc(
    prompt: str, model_str: str = OpenAIModels.mini
) -> tuple[object, str] | None:
    """Generate, validate, and evaluate Wolfram Language code.

    Args:
        prompt: Natural-language description of the desired computation.
        model_str: OpenAI model name used for code generation.

    Returns:
        The Wolfram result and cleaned TeX output, or None for plot, syntax,
        kernel startup, or OpenAI connection failures.
    """
    logger.info('Logger level: %s', logging.getLevelName(logger.level))
    prompt = _trim_leading_whitespace(prompt)
    prompt, save_names = _parse_saveas(prompt)
    slash_commands, prompt = _parse_slash_commands(prompt)
    if save_names and any(
        command in {'code', 'tex', 'help'} for command in slash_commands
    ):
        raise ValueError('/saveas requires an evaluating pipeline')
    show_code = 'showcode' in slash_commands
    show_tex = 'showtex' in slash_commands
    if show_code or show_tex:
        valid_commands = {'calc', 'showcode', 'showtex'}
        if (
            'calc' not in slash_commands
            or not set(slash_commands) <= valid_commands
        ):
            raise ValueError('/showcode and /showtex require /calc')
        slash_commands = ['calc']
    if (
        not slash_commands
        or any(command not in {'help', 'tex'} for command in slash_commands)
    ) and not _start_wolfram_session():
        return None
    natural_language = not slash_commands or all(
        command in {'code', 'calc'} for command in slash_commands
    )
    both_sides = False
    if natural_language:
        prompt, both_sides = _expand_result_references(prompt)
    try:
        if both_sides:
            if 'code' in slash_commands:
                raise ValueError('!bothsides requires an evaluating pipeline')
            result = _wnlc_both_sides_pipeline(
                prompt, model_str, compact='calc' in slash_commands,
                show_code=show_code, show_tex=show_tex,
            )
            _save_results_if_successful(save_names, result)
            return result
        if show_code or show_tex:
            result = _wnlc_calc_pipeline(
                prompt, model_str, show_code=show_code, show_tex=show_tex
            )
            _save_results_if_successful(save_names, result)
            return None
        if slash_commands:
            logger.info('Found slash command(s): %s', ', '.join(slash_commands))
            for command in slash_commands:
                slash_command_pipeline = _SLASH_COMMANDS[command]
                result = slash_command_pipeline(prompt, model_str)
            _save_results_if_successful(save_names, result)
        else:
            result = _wnlc_default_pipeline(prompt, model_str)
            _save_results_if_successful(save_names, result)
            return result
    except APIConnectionError:
        logger.debug('OpenAI API connection failed', exc_info=True)
        display(Markdown(
            '**Could not reach OpenAI.** Check your connection and try again. '
            'If you are connected, check your proxy or firewall settings.'
        ))
        return None


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
    """Pipeline for the /run slash command."""
    logger.info('Executing /run pipeline...')
    validated_response_str: str = _validate_user_wolfram_code(
        prompt, model_str
    )
    if not validated_response_str:
        _handle_wolfram_validation_error(prompt)
        return None
    _display_generated_code(validated_response_str)
    logger.info('Evaluating code...')
    result: object = _evaluate_and_remember(validated_response_str)
    cleaned_tex_str: str = _extract_mathjax_safe_tex(result)
    equation_tex_str: str = _build_equation_tex(
        cleaned_tex_str, unwrap_full_simplify=True
    )
    _default_display_results(result, equation_tex_str)
    return result, cleaned_tex_str


def _wnlc_calc_pipeline(
    prompt: str, model_str: str, show_code: bool = False, show_tex: bool = False
) -> tuple[object, str] | None:
    """Pipeline for the /calc slash command."""
    logger.info('Executing /calc pipeline...')
    validated_response_str, response_str = _generate_validated_wolfram_code(
        prompt, model_str
    )
    if not validated_response_str:
        _handle_wolfram_validation_error(response_str)
        return None
    if show_code:
        _display_generated_code(validated_response_str)
    logger.info('Checking for plot code...')
    if check_contains_plot_code(validated_response_str):
        _generate_plot_from_wolfram_code(validated_response_str)
        return None
    logger.info('Evaluating code...')
    result: object = _evaluate_and_remember(validated_response_str)
    cleaned_tex_str: str = _extract_mathjax_safe_tex(result)
    equation_tex_str: str = _build_equation_tex(
        cleaned_tex_str, unwrap_full_simplify=True
    )
    if show_tex:
        _display_generated_tex(equation_tex_str)
    _display_result_only(equation_tex_str)
    return result, cleaned_tex_str


def _wnlc_help_pipeline(
    prompt: str, model_str: str
) -> tuple[object, str] | None:
    """Stub pipeline for the /help slash command."""
    logger.info('Executing /help pipeline...')
    _display_help_message()
    return None


def _display_help_message() -> None:
    """Display the slash-command help message."""
    display(Markdown(_HELP_MESSAGE_PATH.read_text(encoding='utf-8')))


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
    result: object = _evaluate_and_remember(validated_response_str)
    cleaned_tex_str: str = _extract_mathjax_safe_tex(result)
    equation_tex_str: str = _build_equation_tex(
        cleaned_tex_str, unwrap_full_simplify=True
    )
    _default_display_results(result, equation_tex_str)
    return result, cleaned_tex_str


def _wnlc_both_sides_pipeline(
    prompt: str, model_str: str, compact: bool = False,
    show_code: bool = False, show_tex: bool = False,
) -> tuple[object, str] | None:
    """Apply one generated operation to each side of the previous result."""
    code, response = _generate_validated_wolfram_code(prompt, model_str)
    if not code:
        _handle_wolfram_validation_error(response)
        return None
    if not re.search(r'(?<![\w`])rhs(?![\w`])', code):
        raise ValueError('Generated code did not use the !bothsides reference')
    if check_contains_plot_code(code):
        raise ValueError('!bothsides does not support plot operations')
    left_code = f'With[{{rhs = ReleaseHold[lhs]}}, {code}]'
    if not compact or show_code:
        _display_generated_code(f'{left_code}\n{code}')
    left_result = ws.evaluate(wlexpr(left_code))
    if left_result == WLSymbol('$Failed'):
        _handle_wolfram_validation_error(left_code)
        return None
    right_result = _evaluate_and_remember(code, left_result)
    if right_result == WLSymbol('$Failed'):
        _handle_wolfram_validation_error(code)
        return None
    equation_tex = (
        f'{_extract_mathjax_safe_tex(left_result)} = '
        f'{_extract_mathjax_safe_tex(right_result)}'
    )
    if show_tex:
        _display_generated_tex(equation_tex)
    if compact:
        _display_result_only(equation_tex)
    else:
        _default_display_results((left_result, right_result), equation_tex)
    return (left_result, right_result), equation_tex


def _evaluate_and_remember(
    expr: str, left_result: object = _NO_LEFT_RESULT
) -> object:
    """Evaluate once, then save held lhs and evaluated rhs in Wolfram."""
    global _LAST_RESULT_AVAILABLE
    result = ws.evaluate(wlexpr(f'PyDeriveHelper`pending = ({expr})'))
    if result == WLSymbol('$Failed'):
        return result
    held_input = (
        _hold_input(expr)
        if left_result is _NO_LEFT_RESULT
        else wl.HoldComplete(left_result)
    )
    ws.evaluate(wl.Set(WLSymbol('Global`lhs'), held_input))
    ws.evaluate(wlexpr('Global`rhs = PyDeriveHelper`pending'))
    _LAST_RESULT_AVAILABLE = True
    return result


def _save_results_if_successful(
    names: list[str], result: tuple[object, str] | None
) -> None:
    """Save the current rhs after an evaluating pipeline succeeds."""
    if not names:
        return
    if result is None or result[0] == WLSymbol('$Failed'):
        raise ValueError('/saveas requires a successful non-plot result')
    for name in names:
        ws.evaluate(wl.Set(WLSymbol(f'Global`{name}'), WLSymbol('Global`rhs')))
        _SAVED_RESULT_NAMES.add(name)
    saved_names = ', '.join(f'**!{name}**' for name in names)
    display(Markdown(f'Saved as {saved_names}'))


def _hold_input(expr: str) -> object:
    """Hold the input and snapshot prior lhs/rhs references within it."""
    held_input = wl.ToExpression(expr, wl.InputForm, wl.HoldComplete)
    if not _LAST_RESULT_AVAILABLE:
        return held_input
    previous_lhs = WLSymbol('PyDeriveHelper`previousLhs')
    previous_rhs = WLSymbol('PyDeriveHelper`previousRhs')
    return wl.With(
        wl.List(
            wl.Set(previous_lhs, WLSymbol('Global`lhs')),
            wl.Set(previous_rhs, WLSymbol('Global`rhs')),
        ),
        wl.ReplaceAll(
            held_input,
            wl.List(
                wl.Rule(wl.HoldPattern(WLSymbol('Global`lhs')), previous_lhs),
                wl.Rule(wl.HoldPattern(WLSymbol('Global`rhs')), previous_rhs),
            ),
        ),
    )


# =============================================================================
# Slash command configuration
# =============================================================================

_SlashCommandPipeline = Callable[[str, str], tuple[object, str] | None]

_SLASH_COMMANDS: dict[str, _SlashCommandPipeline] = {
    'code': _wnlc_code_pipeline,
    'tex': _wnlc_tex_pipeline,
    'run': _wnlc_run_pipeline,
    'calc': _wnlc_calc_pipeline,
    'help': _wnlc_help_pipeline,
}
_DISPLAY_OPTIONS = {'showcode', 'showtex'}


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


def _validate_user_wolfram_code(
    candidate_code: str, model_str: str = OpenAIModels.mini
) -> str:
    """Sanitize and validate user-provided Wolfram Language code."""
    wolfram_code_sanitizer: WolframCodeSanitizer = WolframCodeSanitizer(
        _MATH_ASSISTANT_CLIENT, model_str
    )
    wolfram_code_fixer: WolframCodeFixer = WolframCodeFixer(
        _MATH_ASSISTANT_CLIENT, model_str
    )

    logger.info('Sanitizing user-provided code...')
    sanitized_candidate_code: str = wolfram_code_sanitizer.call(candidate_code)

    logger.info('Validating user-provided code...')
    validated_candidate_code: str = _validate_or_fix_wolfram_code(
        sanitized_candidate_code, wolfram_code_fixer
    )
    return validated_candidate_code


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
    if result == WLSymbol('$Failed'):
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


def _build_equation_tex(
    result_tex: str, unwrap_full_simplify: bool = False
) -> str:
    """Format the saved held input and its result as a TeX equation."""
    held_expr = WLSymbol('Global`lhs')
    if unwrap_full_simplify:
        held_expr = wl.Replace(
            held_expr,
            wlexpr('HoldComplete[FullSimplify[inner_]] :> HoldComplete[inner]'),
        )
    is_indefinite_integral: bool = ws.evaluate(
        wl.MatchQ(held_expr, wlexpr('HoldComplete[Integrate[_, _Symbol]]'))
    )
    display_expr = wl.ReplaceRepeated(
        held_expr,
        wl.List(
            wlexpr(
                'HoldPattern[ReleaseHold[HoldComplete[inner_]]] :> '
                'HoldForm[inner]'
            ),
            wlexpr('HoldComplete[inner_] :> HoldForm[inner]'),
        ),
    )
    input_tex: str = str(ws.evaluate(wl.ToString(wl.TeXForm(display_expr))))
    input_tex = _fix_fbox(_fix_hypergeometric_functions(input_tex))
    input_tex = _parenthesize_saved_variables(input_tex)
    if is_indefinite_integral:
        result_tex = f'{result_tex} + C'
    return f'{input_tex} = {result_tex}'


def _parenthesize_saved_variables(tex_str: str) -> str:
    """Wrap saved names in parentheses without changing TeX commands."""
    def replace_symbol(match: re.Match[str]) -> str:
        rendered_symbol = match.group(0)
        name = match.group(1) or rendered_symbol
        if name in _SAVED_RESULT_NAMES:
            return rf'\left({rendered_symbol}\right)'
        return rendered_symbol

    return re.sub(
        r'\\text\{([A-Za-z][A-Za-z0-9]*)\}|\\[A-Za-z]+|[A-Za-z][A-Za-z0-9]*',
        replace_symbol,
        tex_str,
    )


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
_RESULT_REFERENCE_PATTERN: re.Pattern[str] = re.compile(
    r'(?<!!)(?<!\w)!([A-Za-z_][A-Za-z_0-9]*)\b'
)
_SAVEAS_PATTERN: re.Pattern[str] = re.compile(r'(?<!\S)/saveas\b')
_SAVED_NAME_PATTERN: re.Pattern[str] = re.compile(r'[A-Za-z][A-Za-z0-9]*')


def _trim_leading_whitespace(text: str) -> str:
    """Remove leading whitespace from text."""
    return text.lstrip()


def _parse_saveas(prompt: str) -> tuple[str, list[str]]:
    """Remove one /saveas command and return its validated names."""
    commands = list(_SAVEAS_PATTERN.finditer(prompt))
    if not commands:
        return prompt, []
    if len(commands) > 1:
        raise ValueError('Only one /saveas command is allowed')
    command = commands[0]
    arguments = re.match(r'(?:[ \t]+![^\s]+)+', prompt[command.end():])
    if arguments is None:
        raise ValueError('/saveas requires one or more !name arguments')
    names = [token[1:] for token in arguments.group().split()]
    if any(
        _SAVED_NAME_PATTERN.fullmatch(name) is None
        or name in {'result', 'bothsides', 'lhs', 'rhs'}
        for name in names
    ):
        raise ValueError(
            'Saved names must start with a letter and contain only letters '
            'and digits; result, bothsides, lhs, and rhs are reserved'
        )
    end = command.end() + arguments.end()
    if re.match(r'\s+!', prompt[end:]):
        raise ValueError('Separate /saveas names with spaces or tabs only')
    return (prompt[:command.start()] + prompt[end:]).strip(), names


def _expand_result_references(prompt: str) -> tuple[str, bool]:
    """Replace natural-language result references with Wolfram symbols."""
    references = set(_RESULT_REFERENCE_PATTERN.findall(prompt))
    if not references:
        return re.sub(r'(?<!\w)!!(?=[A-Za-z_])', '!', prompt), False
    if references & {'result', 'bothsides'} and not _LAST_RESULT_AVAILABLE:
        raise ValueError('No previous successful calculation to reference')
    if {'result', 'bothsides'} <= references:
        raise ValueError('Use !result or !bothsides, not both in one prompt')
    unknown = references - {'result', 'bothsides'} - _SAVED_RESULT_NAMES
    if unknown:
        raise ValueError(f'Unknown saved result: !{sorted(unknown)[0]}')
    expanded = _RESULT_REFERENCE_PATTERN.sub(
        lambda match: (
            'rhs' if match.group(1) in {'result', 'bothsides'}
            else match.group(1)
        ),
        prompt,
    )
    expanded = re.sub(r'(?<!\w)!!(?=[A-Za-z_])', '!', expanded)
    expanded += (
        '\nThe substituted symbols are Wolfram Language variables holding '
        'saved results. Use them directly in the generated expression.'
    )
    if 'result' in references:
        expanded += (
            '\nThe rhs variable is the previous result. Apply the requested '
            'operation to rhs. Do not use lhs or introduce an equation unless '
            'the description explicitly asks for one.'
        )
    return expanded, 'bothsides' in references


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
        if command_name not in _SLASH_COMMANDS and command_name not in _DISPLAY_OPTIONS:
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


def _default_display_results(result: object, equation_tex_str: str) -> None:
    """Display the evaluated result and its TeX equation.

    Args:
        result: The evaluated Wolfram result.
        equation_tex_str: TeX equation containing the input and result.
    """
    display(Markdown('\n**Raw Evaluated Result**:\n'))
    display(Markdown(f'```plaintext\n{result!s}\n```'))
    display(Markdown('\n**Raw TeX**:\n'))
    display(Markdown(f'```tex\n{equation_tex_str}\n```'))
    display(Markdown('---'))
    display(Markdown('\n**Rendered Equation**:\n'))
    display(Markdown(f'$$\\Large {equation_tex_str}$$'))
    display(Markdown('---'))


def _display_result_only(equation_tex_str: str) -> None:
    """Display only the rendered equation.

    Args:
        equation_tex_str: TeX equation containing the input and result.
    """
    display(Markdown(f'$$\\Large {equation_tex_str}$$'))


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
