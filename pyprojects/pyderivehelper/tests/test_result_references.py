import os
from collections.abc import Iterator
from unittest.mock import patch

from httpx2 import Request
from openai import APIConnectionError
import pytest

os.environ.setdefault('OPENAI_PERSONAL_MATH_ASSISTANT', 'test-key')

from pyderivehelper import wltools  # noqa: E402


@pytest.fixture(autouse=True)
def patch_kernel_start() -> Iterator[None]:
    with patch.object(wltools.ws, 'start'):
        yield



def test_kernel_start_failure_is_displayed_before_work() -> None:
    with (
        patch.object(
            wltools.ws, 'start',
            side_effect=wltools.WolframKernelException('startup failed'),
        ) as start,
        patch.object(wltools, 'display') as display,
        patch.object(wltools, '_evaluate_and_remember') as evaluate,
        patch.object(wltools, '_generate_validated_wolfram_code') as generate,
    ):
        assert wltools.wc('1+1') is None
        assert wltools.wnlc('/calc add one and one') is None

    assert start.call_count == 2
    evaluate.assert_not_called()
    generate.assert_not_called()
    assert display.call_count == 2
    assert 'could not start' in display.call_args.args[0].data


def test_openai_connection_failure_displays_message() -> None:
    error = APIConnectionError(
        request=Request('POST', 'https://api.openai.com/v1/responses')
    )
    with (
        patch.object(wltools, '_wnlc_default_pipeline', side_effect=error),
        patch.object(wltools, 'display') as display,
    ):
        assert wltools.wnlc('Take the derivative of sin(x)') is None

    display.assert_called_once()
    assert 'Could not reach OpenAI' in display.call_args.args[0].data


def test_help_and_tex_skip_kernel_start() -> None:
    with (
        patch.object(wltools.ws, 'start') as start,
        patch.object(wltools, '_display_help_message'),
        patch.object(
            wltools, '_generate_validated_tex_code',
            return_value=('x^2', 'x^2'),
        ),
        patch.object(wltools, '_display_generated_tex'),
    ):
        assert wltools.wnlc('/help') is None
        assert wltools.wnlc('/tex x squared') is None

    start.assert_not_called()


def test_wc_evaluates_once_and_updates_both_symbols() -> None:
    with (
        patch.object(
            wltools.ws, 'evaluate', side_effect=[2, None, None]
        ) as evaluate,
        patch.object(wltools, '_extract_mathjax_safe_tex', return_value='2'),
        patch.object(wltools, '_build_equation_tex', return_value='1+1=2'),
        patch.object(wltools, '_default_display_results'),
        patch.object(wltools, '_LAST_RESULT_AVAILABLE', False),
    ):
        assert wltools.wc('1+1') == 2
        assert evaluate.call_count == 3
        assert '1+1' in str(evaluate.call_args_list[0].args[0])
        assert 'Global`lhs' in str(evaluate.call_args_list[1].args[0])
        assert 'Global`rhs' in str(evaluate.call_args_list[2].args[0])
        assert wltools._LAST_RESULT_AVAILABLE


def test_failed_evaluation_keeps_previous_history() -> None:
    with (
        patch.object(
            wltools.ws, 'evaluate', return_value=wltools.WLSymbol('$Failed')
        ) as evaluate,
        patch.object(wltools, '_LAST_RESULT_AVAILABLE', False),
    ):
        assert wltools._evaluate_and_remember('bad[]') == wltools.WLSymbol('$Failed')
        evaluate.assert_called_once()
        assert not wltools._LAST_RESULT_AVAILABLE


def test_validation_recognizes_wolfram_failure_symbol() -> None:
    with patch.object(
        wltools.ws, 'evaluate', return_value=wltools.WLSymbol('$Failed')
    ):
        assert not wltools.validate_wolfram_code('bad[]')


def test_previous_symbols_are_snapshotted_in_held_input() -> None:
    with (
        patch.object(
            wltools.ws, 'evaluate', side_effect=[3, None, None]
        ) as evaluate,
        patch.object(wltools, '_LAST_RESULT_AVAILABLE', True),
    ):
        wltools._evaluate_and_remember('rhs + ReleaseHold[lhs]')
        assert 'ReplaceAll' in str(evaluate.call_args_list[1].args[0])


def test_equation_displays_saved_references_under_hold() -> None:
    with (
        patch.object(
            wltools.ws, 'evaluate', side_effect=[False, 'expanded input']
        ) as evaluate,
    ):
        assert wltools._build_equation_tex('9') == 'expanded input = 9'
    display_call = str(evaluate.call_args_list[1].args[0])
    assert 'Global`lhs' in display_call
    assert 'ReplaceRepeated' in display_call
    assert 'ReleaseHold[HoldComplete' in display_call
    assert 'HoldForm' in display_call


def test_references_require_history_and_honor_literal_escape() -> None:
    with patch.object(wltools, '_LAST_RESULT_AVAILABLE', False):
        with pytest.raises(ValueError):
            wltools._expand_result_references('Integrate !result')
    with patch.object(wltools, '_LAST_RESULT_AVAILABLE', True):
        prompt, both_sides = wltools._expand_result_references(
            'Integrate !bothsides; print !!result literally'
        )
        assert both_sides
        assert 'Integrate rhs' in prompt
        assert '!result literally' in prompt


def test_saveas_parses_multiple_names() -> None:
    prompt, names = wltools._parse_saveas(
        '/calc Integrate x /saveas\t!myVar1  !myVar2'
    )
    assert prompt == '/calc Integrate x'
    assert names == ['myVar1', 'myVar2']


@pytest.mark.parametrize(
    'prompt',
    [
        'Integrate x /saveas !a /saveas !b',
        'Integrate x /saveas\n!a',
        'Integrate x /saveas !a\n!b',
        'Integrate x /saveas !bad-name',
        'Integrate x /saveas !my_var',
        'Integrate x /saveas !_myVar',
        'Integrate x /saveas !myVar_',
        'Integrate x /saveas !1myVar',
        'Integrate x /saveas !result',
        'Integrate x /saveas !bothsides',
        'Integrate x /saveas !lhs',
        'Integrate x /saveas !rhs',
    ],
)
def test_saveas_rejects_invalid_commands(prompt: str) -> None:
    with pytest.raises(ValueError):
        wltools._parse_saveas(prompt)


def test_saveas_uses_user_names_as_wolfram_symbols() -> None:
    with (
        patch.object(wltools, '_SAVED_RESULT_NAMES', set()),
        patch.object(wltools, '_wnlc_default_pipeline', return_value=(2, '2'))
        as pipeline,
        patch.object(wltools.ws, 'evaluate') as evaluate,
    ):
        wltools.wnlc('Integrate x /saveas !poly1 !expandedPoly')
        assert pipeline.call_args.args[0] == 'Integrate x'
        assert evaluate.call_count == 2
        assert [str(call.args[0]) for call in evaluate.call_args_list] == [
            'Set[Global`poly1, Global`rhs]',
            'Set[Global`expandedPoly, Global`rhs]',
        ]
        prompt, _ = wltools._expand_result_references(
            'Add !poly1 to !expandedPoly'
        )
        assert prompt.splitlines()[0] == 'Add poly1 to expandedPoly'
        wltools.wnlc('Integrate x^2 /saveas !poly1')
        assert str(evaluate.call_args.args[0]) == 'Set[Global`poly1, Global`rhs]'
        assert wltools._SAVED_RESULT_NAMES == {'poly1', 'expandedPoly'}


@pytest.mark.parametrize('name', ['poly_name', '_poly', 'poly_'])
def test_underscore_references_are_not_partially_expanded(name: str) -> None:
    with patch.object(wltools, '_SAVED_RESULT_NAMES', {'poly'}):
        with pytest.raises(ValueError):
            wltools._expand_result_references(f'Evaluate !{name}')


def test_saveas_requires_a_successful_evaluating_pipeline() -> None:
    with patch.object(wltools, '_wnlc_default_pipeline', return_value=None):
        with pytest.raises(ValueError):
            wltools.wnlc('Plot x /saveas !plot')
    with pytest.raises(ValueError):
        wltools.wnlc('/code Integrate x /saveas !integral')
    with pytest.raises(ValueError):
        wltools._expand_result_references('Integrate !missing')


def test_calc_display_options_still_save_result() -> None:
    with (
        patch.object(wltools, '_wnlc_calc_pipeline', return_value=(2, '2'))
        as pipeline,
        patch.object(wltools, '_save_results_if_successful') as save,
    ):
        result = wltools.wnlc('/calc /showcode Integrate x /saveas !area')
        assert result is None
        assert pipeline.call_args.args[0] == 'Integrate x'
        save.assert_called_once_with(['area'], (2, '2'))


def test_both_sides_runs_the_same_operation_and_displays_equation() -> None:
    with (
        patch.object(
            wltools, '_generate_validated_wolfram_code',
            return_value=('Integrate[rhs, x]', 'Integrate[rhs, x]'),
        ),
        patch.object(wltools.ws, 'evaluate', return_value=3) as evaluate,
        patch.object(
            wltools, '_evaluate_and_remember', return_value=3
        ) as remember,
        patch.object(wltools, '_extract_mathjax_safe_tex', return_value='3'),
        patch.object(wltools, '_display_generated_code') as display_code,
        patch.object(wltools, '_display_generated_tex') as display_tex,
        patch.object(wltools, '_display_result_only') as display_result,
    ):
        result = wltools._wnlc_both_sides_pipeline(
            'Integrate rhs', 'model', True,
            show_code=True, show_tex=True,
        )
        assert result == ((3, 3), '3 = 3')
        assert 'ReleaseHold[lhs]' in str(evaluate.call_args.args[0])
        remember.assert_called_once_with('Integrate[rhs, x]', 3)
        assert 'Integrate[rhs, x]' in display_code.call_args.args[0]
        display_tex.assert_called_once_with('3 = 3')
        display_result.assert_called_once_with('3 = 3')


def test_wnlc_routes_both_sides_reference() -> None:
    with (
        patch.object(wltools, '_LAST_RESULT_AVAILABLE', True),
        patch.object(
            wltools, '_wnlc_both_sides_pipeline', return_value=((1, 1), '1 = 1')
        ) as pipeline,
    ):
        result = wltools.wnlc('/calc Integrate !bothsides with respect to x')
        assert result == ((1, 1), '1 = 1')
        assert 'Integrate rhs' in pipeline.call_args.args[0]
        assert pipeline.call_args.kwargs['compact']


def test_wnlc_routes_result_reference() -> None:
    with (
        patch.object(wltools, '_LAST_RESULT_AVAILABLE', True),
        patch.object(
            wltools, '_wnlc_default_pipeline', return_value=(2, '2')
        ) as pipeline,
    ):
        assert wltools.wnlc('Integrate !result') == (2, '2')
        assert 'Integrate rhs' in pipeline.call_args.args[0]


def test_calc_display_options_preserve_result_reference() -> None:
    with (
        patch.object(wltools, '_LAST_RESULT_AVAILABLE', True),
        patch.object(
            wltools, '_wnlc_calc_pipeline', return_value=(2, '2')
        ) as pipeline,
    ):
        result = wltools.wnlc('/showtex /calc /showcode Integrate !result')
        assert result is None
        assert 'Integrate rhs' in pipeline.call_args.args[0]
        assert pipeline.call_args.kwargs == {'show_code': True, 'show_tex': True}


def test_calc_display_options_reuse_generated_output() -> None:
    with (
        patch.object(
            wltools, '_generate_validated_wolfram_code',
            return_value=('Integrate[rhs, x]', 'Integrate[rhs, x]'),
        ) as generate,
        patch.object(wltools, 'check_contains_plot_code', return_value=False),
        patch.object(
            wltools, '_evaluate_and_remember', return_value='result'
        ) as evaluate,
        patch.object(wltools, '_extract_mathjax_safe_tex', return_value='x'),
        patch.object(wltools, '_build_equation_tex', return_value='I = x'),
        patch.object(wltools, '_display_generated_code') as display_code,
        patch.object(wltools, '_display_generated_tex') as display_tex,
        patch.object(wltools, '_display_result_only') as display_result,
    ):
        result = wltools._wnlc_calc_pipeline(
            'Integrate rhs', 'model', show_code=True, show_tex=True
        )
        assert result == ('result', 'x')
        generate.assert_called_once_with('Integrate rhs', 'model')
        evaluate.assert_called_once_with('Integrate[rhs, x]')
        display_code.assert_called_once_with('Integrate[rhs, x]')
        display_tex.assert_called_once_with('I = x')
        display_result.assert_called_once_with('I = x')


def test_calc_display_options_apply_to_both_sides() -> None:
    with (
        patch.object(wltools, '_LAST_RESULT_AVAILABLE', True),
        patch.object(
            wltools, '_wnlc_both_sides_pipeline', return_value=((1, 1), '1 = 1')
        ) as pipeline,
    ):
        wltools.wnlc('/calc /showcode /showtex Integrate !bothsides')
        assert 'Integrate rhs' in pipeline.call_args.args[0]
        assert pipeline.call_args.kwargs == {
            'compact': True,
            'show_code': True,
            'show_tex': True,
        }


@pytest.mark.parametrize(
    'prompt', ['/showcode Integrate x', '/calc /tex /showtex Integrate x']
)
def test_calc_display_options_require_calc(prompt: str) -> None:
    with pytest.raises(ValueError):
        wltools.wnlc(prompt)


def test_showtex_does_not_display_equation_for_plot() -> None:
    with (
        patch.object(
            wltools, '_generate_validated_wolfram_code',
            return_value=('Plot[x, {x, 0, 1}]', 'Plot[x, {x, 0, 1}]'),
        ),
        patch.object(wltools, 'check_contains_plot_code', return_value=True),
        patch.object(wltools, '_generate_plot_from_wolfram_code') as plot,
        patch.object(wltools, '_display_generated_code') as display_code,
        patch.object(wltools, '_display_generated_tex') as display_tex,
    ):
        wltools._wnlc_calc_pipeline(
            'Plot x', 'model', show_code=True, show_tex=True
        )
        display_code.assert_called_once_with('Plot[x, {x, 0, 1}]')
        plot.assert_called_once_with('Plot[x, {x, 0, 1}]')
        display_tex.assert_not_called()
