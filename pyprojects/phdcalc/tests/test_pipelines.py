from unittest.mock import patch

import pytest
from phdcalc import wltools


@pytest.mark.parametrize(
    ('pipeline', 'generator', 'error_handler'),
    [
        ('_wnlc_code_pipeline', '_generate_validated_wolfram_code',
         '_handle_wolfram_validation_error'),
        ('_wnlc_tex_pipeline', '_generate_validated_tex_code',
         '_handle_tex_validation_error'),
        ('_wnlc_default_pipeline', '_generate_validated_wolfram_code',
         '_handle_wolfram_validation_error'),
        ('_wnlc_calc_pipeline', '_generate_validated_wolfram_code',
         '_handle_wolfram_validation_error'),
    ],
)
def test_pipeline_reports_unfixable_generation(
    pipeline: str, generator: str, error_handler: str
) -> None:
    with (
        patch.object(wltools, generator, return_value=('', 'original')),
        patch.object(wltools, error_handler) as show_error,
    ):
        assert getattr(wltools, pipeline)('prompt', 'model') is None
    show_error.assert_called_once_with('original')


def test_code_and_tex_pipelines_display_validated_output() -> None:
    with (
        patch.object(
            wltools, '_generate_validated_wolfram_code',
            return_value=('valid code', 'raw code'),
        ),
        patch.object(wltools, '_display_generated_code') as display_code,
        patch.object(
            wltools, '_generate_validated_tex_code',
            return_value=('valid tex', 'raw tex'),
        ),
        patch.object(wltools, '_display_generated_tex') as display_tex,
    ):
        assert wltools._wnlc_code_pipeline('prompt', 'model') == (None, 'valid code')
        assert wltools._wnlc_tex_pipeline('prompt', 'model') == (None, 'valid tex')
    display_code.assert_called_once_with('valid code')
    display_tex.assert_called_once_with('valid tex')


def test_run_pipeline_evaluates_validated_user_code() -> None:
    with (
        patch.object(wltools, '_validate_user_wolfram_code', return_value='x + 1'),
        patch.object(wltools, '_evaluate_and_remember', return_value=3) as evaluate,
        patch.object(wltools, '_extract_mathjax_safe_tex', return_value='3'),
        patch.object(wltools, '_build_equation_tex', return_value='x+1=3')
        as equation,
        patch.object(wltools, '_display_generated_code'),
        patch.object(wltools, '_default_display_results') as display,
    ):
        assert wltools._wnlc_run_pipeline('user code', 'model') == (3, '3')
    evaluate.assert_called_once_with('x + 1')
    equation.assert_called_once_with('3', unwrap_full_simplify=True)
    display.assert_called_once_with(3, 'x+1=3')


def test_run_pipeline_does_not_evaluate_invalid_code() -> None:
    with (
        patch.object(wltools, '_validate_user_wolfram_code', return_value=''),
        patch.object(wltools, '_handle_wolfram_validation_error') as show_error,
        patch.object(wltools, '_evaluate_and_remember') as evaluate,
    ):
        assert wltools._wnlc_run_pipeline('bad code', 'model') is None
    show_error.assert_called_once_with('bad code')
    evaluate.assert_not_called()


@pytest.mark.parametrize('pipeline', ['_wnlc_default_pipeline', '_wnlc_calc_pipeline'])
def test_generated_plot_skips_evaluation(pipeline: str) -> None:
    with (
        patch.object(
            wltools, '_generate_validated_wolfram_code',
            return_value=('Plot[x, {x, 0, 1}]', 'raw'),
        ),
        patch.object(wltools, 'check_contains_plot_code', return_value=True),
        patch.object(wltools, '_generate_plot_from_wolfram_code') as plot,
        patch.object(wltools, '_evaluate_and_remember') as evaluate,
        patch.object(wltools, '_display_generated_code'),
    ):
        assert getattr(wltools, pipeline)('plot', 'model') is None
    plot.assert_called_once_with('Plot[x, {x, 0, 1}]')
    evaluate.assert_not_called()


def test_default_pipeline_displays_evaluated_result() -> None:
    with (
        patch.object(
            wltools, '_generate_validated_wolfram_code',
            return_value=('x + 1', 'raw'),
        ),
        patch.object(wltools, 'check_contains_plot_code', return_value=False),
        patch.object(wltools, '_evaluate_and_remember', return_value=3),
        patch.object(wltools, '_extract_mathjax_safe_tex', return_value='3'),
        patch.object(wltools, '_build_equation_tex', return_value='x+1=3'),
        patch.object(wltools, '_display_generated_code'),
        patch.object(wltools, '_default_display_results') as display,
    ):
        assert wltools._wnlc_default_pipeline('add one', 'model') == (3, '3')
    display.assert_called_once_with(3, 'x+1=3')


def test_both_sides_rejects_unrelated_code_and_plots() -> None:
    with patch.object(
        wltools, '_generate_validated_wolfram_code',
        return_value=('x + 1', 'raw'),
    ):
        with pytest.raises(ValueError, match='did not use'):
            wltools._wnlc_both_sides_pipeline('prompt', 'model')
    with (
        patch.object(
            wltools, '_generate_validated_wolfram_code',
            return_value=('Plot[rhs, {x, 0, 1}]', 'raw'),
        ),
        patch.object(wltools, 'check_contains_plot_code', return_value=True),
    ):
        with pytest.raises(ValueError, match='plot operations'):
            wltools._wnlc_both_sides_pipeline('prompt', 'model')


@pytest.mark.parametrize('failed_side', ['left', 'right'])
def test_both_sides_stops_after_failed_evaluation(failed_side: str) -> None:
    failed = wltools.WLSymbol('$Failed')
    with (
        patch.object(
            wltools, '_generate_validated_wolfram_code',
            return_value=('rhs + 1', 'raw'),
        ),
        patch.object(wltools, 'check_contains_plot_code', return_value=False),
        patch.object(wltools.ws, 'evaluate', return_value=failed if failed_side == 'left' else 2),
        patch.object(wltools, '_evaluate_and_remember', return_value=failed)
        as remember,
        patch.object(wltools, '_display_generated_code'),
        patch.object(wltools, '_handle_wolfram_validation_error') as show_error,
    ):
        assert wltools._wnlc_both_sides_pipeline('prompt', 'model') is None
    if failed_side == 'left':
        remember.assert_not_called()
    else:
        remember.assert_called_once()
    show_error.assert_called_once()


def test_slash_command_parser_ignores_commands_after_unknown() -> None:
    commands, prompt = wltools._parse_slash_commands('/run /unknown /calc x')
    assert commands == ['run']
    assert prompt == 'x'


def test_result_reference_rejects_both_reference_forms_together() -> None:
    with patch.object(wltools, '_LAST_RESULT_AVAILABLE', True):
        with pytest.raises(ValueError, match='not both'):
            wltools._expand_result_references('Add !result to !bothsides')


def test_both_sides_cannot_run_in_code_only_mode() -> None:
    with patch.object(wltools, '_LAST_RESULT_AVAILABLE', True):
        with pytest.raises(ValueError, match='evaluating pipeline'):
            wltools.wnlc('/code Integrate !bothsides')


def test_both_sides_reports_unfixable_generated_code() -> None:
    with (
        patch.object(
            wltools, '_generate_validated_wolfram_code',
            return_value=('', 'raw'),
        ),
        patch.object(wltools, '_handle_wolfram_validation_error') as show_error,
    ):
        assert wltools._wnlc_both_sides_pipeline('prompt', 'model') is None
    show_error.assert_called_once_with('raw')


def test_both_sides_default_view_displays_both_results() -> None:
    with (
        patch.object(
            wltools, '_generate_validated_wolfram_code',
            return_value=('rhs + 1', 'raw'),
        ),
        patch.object(wltools, 'check_contains_plot_code', return_value=False),
        patch.object(wltools.ws, 'evaluate', return_value=2),
        patch.object(wltools, '_evaluate_and_remember', return_value=3),
        patch.object(wltools, '_extract_mathjax_safe_tex', side_effect=['2', '3']),
        patch.object(wltools, '_display_generated_code'),
        patch.object(wltools, '_default_display_results') as display,
    ):
        assert wltools._wnlc_both_sides_pipeline('prompt', 'model') == (
            (2, 3), '2 = 3'
        )
    display.assert_called_once_with((2, 3), '2 = 3')


def test_plot_detection_matches_configured_command() -> None:
    assert wltools.check_contains_plot_code('Plot[x, {x, 0, 1}]', ('Plot',))
    assert not wltools.check_contains_plot_code('x + 1', ('Plot',))


def test_calc_without_showtex_displays_only_result() -> None:
    with (
        patch.object(
            wltools, '_generate_validated_wolfram_code',
            return_value=('x + 1', 'raw'),
        ),
        patch.object(wltools, 'check_contains_plot_code', return_value=False),
        patch.object(wltools, '_evaluate_and_remember', return_value=3),
        patch.object(wltools, '_extract_mathjax_safe_tex', return_value='3'),
        patch.object(wltools, '_build_equation_tex', return_value='x+1=3'),
        patch.object(wltools, '_display_generated_tex') as show_tex,
        patch.object(wltools, '_display_result_only') as show_result,
    ):
        assert wltools._wnlc_calc_pipeline('add one', 'model') == (3, '3')
    show_tex.assert_not_called()
    show_result.assert_called_once_with('x+1=3')


def test_compact_both_sides_hides_generated_code() -> None:
    with (
        patch.object(
            wltools, '_generate_validated_wolfram_code',
            return_value=('rhs + 1', 'raw'),
        ),
        patch.object(wltools, 'check_contains_plot_code', return_value=False),
        patch.object(wltools.ws, 'evaluate', return_value=2),
        patch.object(wltools, '_evaluate_and_remember', return_value=3),
        patch.object(wltools, '_extract_mathjax_safe_tex', side_effect=['2', '3']),
        patch.object(wltools, '_display_generated_code') as show_code,
        patch.object(wltools, '_display_result_only') as show_result,
    ):
        assert wltools._wnlc_both_sides_pipeline(
            'prompt', 'model', compact=True
        ) == ((2, 3), '2 = 3')
    show_code.assert_not_called()
    show_result.assert_called_once_with('2 = 3')
