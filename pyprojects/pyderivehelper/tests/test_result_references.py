import os
import unittest
from unittest.mock import patch

from httpx2 import Request
from openai import APIConnectionError

os.environ.setdefault('OPENAI_PERSONAL_MATH_ASSISTANT', 'test-key')

from pyderivehelper import wltools  # noqa: E402


class ResultReferenceTests(unittest.TestCase):
    def setUp(self) -> None:
        start_patcher = patch.object(wltools.ws, 'start')
        start_patcher.start()
        self.addCleanup(start_patcher.stop)

    def test_kernel_start_failure_is_displayed_before_work(self) -> None:
        with (
            patch.object(
                wltools.ws, 'start',
                side_effect=wltools.WolframKernelException('startup failed'),
            ) as start,
            patch.object(wltools, 'display') as display,
            patch.object(wltools, '_evaluate_and_remember') as evaluate,
            patch.object(wltools, '_generate_validated_wolfram_code') as generate,
        ):
            self.assertIsNone(wltools.wc('1+1'))
            self.assertIsNone(wltools.wnlc('/calc add one and one'))

        self.assertEqual(start.call_count, 2)
        evaluate.assert_not_called()
        generate.assert_not_called()
        self.assertEqual(display.call_count, 2)
        self.assertIn('could not start', display.call_args.args[0].data)

    def test_openai_connection_failure_displays_message(self) -> None:
        error = APIConnectionError(
            request=Request('POST', 'https://api.openai.com/v1/responses')
        )
        with (
            patch.object(wltools, '_wnlc_default_pipeline', side_effect=error),
            patch.object(wltools, 'display') as display,
        ):
            self.assertIsNone(wltools.wnlc('Take the derivative of sin(x)'))

        display.assert_called_once()
        self.assertIn('Could not reach OpenAI', display.call_args.args[0].data)

    def test_help_and_tex_skip_kernel_start(self) -> None:
        with (
            patch.object(wltools.ws, 'start') as start,
            patch.object(wltools, '_display_help_message'),
            patch.object(
                wltools, '_generate_validated_tex_code',
                return_value=('x^2', 'x^2'),
            ),
            patch.object(wltools, '_display_generated_tex'),
        ):
            self.assertIsNone(wltools.wnlc('/help'))
            self.assertIsNone(wltools.wnlc('/tex x squared'))

        start.assert_not_called()

    def test_wc_evaluates_once_and_updates_both_symbols(self) -> None:
        with (
            patch.object(
                wltools.ws, 'evaluate', side_effect=[2, None, None]
            ) as evaluate,
            patch.object(wltools, '_extract_mathjax_safe_tex', return_value='2'),
            patch.object(wltools, '_build_equation_tex', return_value='1+1=2'),
            patch.object(wltools, '_default_display_results'),
            patch.object(wltools, '_LAST_RESULT_AVAILABLE', False),
        ):
            self.assertEqual(wltools.wc('1+1'), 2)
            self.assertEqual(evaluate.call_count, 3)
            self.assertIn('1+1', str(evaluate.call_args_list[0].args[0]))
            self.assertIn('Global`lhs', str(evaluate.call_args_list[1].args[0]))
            self.assertIn('Global`rhs', str(evaluate.call_args_list[2].args[0]))
            self.assertTrue(wltools._LAST_RESULT_AVAILABLE)

    def test_failed_evaluation_keeps_previous_history(self) -> None:
        with (
            patch.object(
                wltools.ws, 'evaluate', return_value=wltools.WLSymbol('$Failed')
            ) as evaluate,
            patch.object(wltools, '_LAST_RESULT_AVAILABLE', False),
        ):
            self.assertEqual(
                wltools._evaluate_and_remember('bad[]'),
                wltools.WLSymbol('$Failed'),
            )
            evaluate.assert_called_once()
            self.assertFalse(wltools._LAST_RESULT_AVAILABLE)

    def test_validation_recognizes_wolfram_failure_symbol(self) -> None:
        with patch.object(
            wltools.ws, 'evaluate', return_value=wltools.WLSymbol('$Failed')
        ):
            self.assertFalse(wltools.validate_wolfram_code('bad[]'))

    def test_previous_symbols_are_snapshotted_in_held_input(self) -> None:
        with (
            patch.object(
                wltools.ws, 'evaluate', side_effect=[3, None, None]
            ) as evaluate,
            patch.object(wltools, '_LAST_RESULT_AVAILABLE', True),
        ):
            wltools._evaluate_and_remember('rhs + ReleaseHold[lhs]')
            self.assertIn('ReplaceAll', str(evaluate.call_args_list[1].args[0]))

    def test_equation_displays_saved_references_under_hold(self) -> None:
        with (
            patch.object(wltools, '_SAVED_SYMBOL_NAMES', {}),
            patch.object(
                wltools.ws, 'evaluate', side_effect=[False, 'expanded input']
            ) as evaluate,
        ):
            self.assertEqual(
                wltools._build_equation_tex('9'), 'expanded input = 9'
            )
        display_call = str(evaluate.call_args_list[1].args[0])
        self.assertIn('Global`lhs', display_call)
        self.assertIn('ReplaceRepeated', display_call)
        self.assertIn('ReleaseHold[HoldComplete', display_call)
        self.assertIn('HoldForm', display_call)

    def test_equation_uses_saved_name_for_display(self) -> None:
        saved_names = {'PyDeriveHelper`savedResult1': 'my_var'}
        with (
            patch.object(wltools, '_SAVED_SYMBOL_NAMES', saved_names),
            patch.object(
                wltools.ws, 'evaluate', side_effect=[False, 'D[my_var,x]']
            ) as evaluate,
        ):
            self.assertEqual(
                wltools._build_equation_tex('1'), 'D[my_var,x] = 1'
            )
        display_call = str(evaluate.call_args_list[1].args[0])
        self.assertIn('HoldPattern[PyDeriveHelper`savedResult1]', display_call)
        self.assertIn('my_var', display_call)

    def test_references_require_history_and_honor_literal_escape(self) -> None:
        with patch.object(wltools, '_LAST_RESULT_AVAILABLE', False):
            with self.assertRaises(ValueError):
                wltools._expand_result_references('Integrate !result')
        with patch.object(wltools, '_LAST_RESULT_AVAILABLE', True):
            prompt, both_sides = wltools._expand_result_references(
                'Integrate !bothsides; print !!result literally'
            )
            self.assertTrue(both_sides)
            self.assertIn('Integrate rhs', prompt)
            self.assertIn('!result literally', prompt)

    def test_saveas_parses_multiple_names_and_rejects_invalid_commands(self) -> None:
        prompt, names = wltools._parse_saveas(
            '/calc Integrate x /saveas\t!myvar1  !my_var2'
        )
        self.assertEqual(prompt, '/calc Integrate x')
        self.assertEqual(names, ['myvar1', 'my_var2'])
        for prompt in (
            'Integrate x /saveas !a /saveas !b',
            'Integrate x /saveas\n!a',
            'Integrate x /saveas !a\n!b',
            'Integrate x /saveas !bad-name',
            'Integrate x /saveas !result',
        ):
            with self.subTest(prompt=prompt), self.assertRaises(ValueError):
                wltools._parse_saveas(prompt)

    def test_saveas_stores_rhs_and_resolves_saved_names(self) -> None:
        with (
            patch.object(wltools, '_SAVED_RESULT_SYMBOLS', {}),
            patch.object(wltools, '_SAVED_SYMBOL_NAMES', {}),
            patch.object(wltools, '_NEXT_SAVED_RESULT_ID', 0),
            patch.object(wltools, '_wnlc_default_pipeline', return_value=(2, '2'))
            as pipeline,
            patch.object(wltools.ws, 'evaluate') as evaluate,
        ):
            wltools.wnlc('Integrate x /saveas !first1 !second_2')
            self.assertEqual(pipeline.call_args.args[0], 'Integrate x')
            self.assertEqual(evaluate.call_count, 2)
            self.assertIn('Global`rhs', str(evaluate.call_args.args[0]))
            first_symbol = wltools._SAVED_RESULT_SYMBOLS['first1']
            second_symbol = wltools._SAVED_RESULT_SYMBOLS['second_2']
            self.assertNotEqual(first_symbol, second_symbol)
            self.assertEqual(wltools._SAVED_SYMBOL_NAMES[first_symbol], 'first1')
            self.assertEqual(wltools._SAVED_SYMBOL_NAMES[second_symbol], 'second_2')
            prompt, _ = wltools._expand_result_references('Add !first1 to !second_2')
            self.assertIn(first_symbol, prompt)
            self.assertIn(second_symbol, prompt)
            wltools.wnlc('Integrate x^2 /saveas !first1')
            self.assertNotEqual(
                first_symbol, wltools._SAVED_RESULT_SYMBOLS['first1']
            )
            self.assertEqual(
                second_symbol, wltools._SAVED_RESULT_SYMBOLS['second_2']
            )
            self.assertEqual(wltools._SAVED_SYMBOL_NAMES[first_symbol], 'first1')

    def test_saveas_requires_a_successful_evaluating_pipeline(self) -> None:
        with patch.object(wltools, '_wnlc_default_pipeline', return_value=None):
            with self.assertRaises(ValueError):
                wltools.wnlc('Plot x /saveas !plot')
        with self.assertRaises(ValueError):
            wltools.wnlc('/code Integrate x /saveas !integral')
        with self.assertRaises(ValueError):
            wltools._expand_result_references('Integrate !missing')

    def test_calc_display_options_still_save_result(self) -> None:
        with (
            patch.object(wltools, '_wnlc_calc_pipeline', return_value=(2, '2'))
            as pipeline,
            patch.object(wltools, '_save_results_if_successful') as save,
        ):
            result = wltools.wnlc('/calc /showcode Integrate x /saveas !area')
            self.assertIsNone(result)
            self.assertEqual(pipeline.call_args.args[0], 'Integrate x')
            save.assert_called_once_with(['area'], (2, '2'))

    def test_both_sides_runs_the_same_operation_and_displays_equation(self) -> None:
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
            self.assertEqual(result, ((3, 3), '3 = 3'))
            self.assertIn('ReleaseHold[lhs]', str(evaluate.call_args.args[0]))
            remember.assert_called_once_with('Integrate[rhs, x]', 3)
            self.assertIn('Integrate[rhs, x]', display_code.call_args.args[0])
            display_tex.assert_called_once_with('3 = 3')
            display_result.assert_called_once_with('3 = 3')

    def test_wnlc_routes_both_sides_reference(self) -> None:
        with (
            patch.object(wltools, '_LAST_RESULT_AVAILABLE', True),
            patch.object(
                wltools, '_wnlc_both_sides_pipeline', return_value=((1, 1), '1 = 1')
            ) as pipeline,
        ):
            result = wltools.wnlc('/calc Integrate !bothsides with respect to x')
            self.assertEqual(result, ((1, 1), '1 = 1'))
            self.assertIn('Integrate rhs', pipeline.call_args.args[0])
            self.assertTrue(pipeline.call_args.kwargs['compact'])

    def test_wnlc_routes_result_reference(self) -> None:
        with (
            patch.object(wltools, '_LAST_RESULT_AVAILABLE', True),
            patch.object(
                wltools, '_wnlc_default_pipeline', return_value=(2, '2')
            ) as pipeline,
        ):
            self.assertEqual(wltools.wnlc('Integrate !result'), (2, '2'))
            self.assertIn('Integrate rhs', pipeline.call_args.args[0])

    def test_calc_display_options_preserve_result_reference(self) -> None:
        with (
            patch.object(wltools, '_LAST_RESULT_AVAILABLE', True),
            patch.object(
                wltools, '_wnlc_calc_pipeline', return_value=(2, '2')
            ) as pipeline,
        ):
            result = wltools.wnlc('/showtex /calc /showcode Integrate !result')
            self.assertIsNone(result)
            self.assertIn('Integrate rhs', pipeline.call_args.args[0])
            self.assertEqual(
                pipeline.call_args.kwargs, {'show_code': True, 'show_tex': True}
            )

    def test_calc_display_options_reuse_generated_output(self) -> None:
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
            self.assertEqual(result, ('result', 'x'))
            generate.assert_called_once_with('Integrate rhs', 'model')
            evaluate.assert_called_once_with('Integrate[rhs, x]')
            display_code.assert_called_once_with('Integrate[rhs, x]')
            display_tex.assert_called_once_with('I = x')
            display_result.assert_called_once_with('I = x')

    def test_calc_display_options_apply_to_both_sides(self) -> None:
        with (
            patch.object(wltools, '_LAST_RESULT_AVAILABLE', True),
            patch.object(
                wltools, '_wnlc_both_sides_pipeline', return_value=((1, 1), '1 = 1')
            ) as pipeline,
        ):
            wltools.wnlc('/calc /showcode /showtex Integrate !bothsides')
            self.assertIn('Integrate rhs', pipeline.call_args.args[0])
            self.assertEqual(
                pipeline.call_args.kwargs,
                {'compact': True, 'show_code': True, 'show_tex': True},
            )

    def test_calc_display_options_require_calc(self) -> None:
        for prompt in ('/showcode Integrate x', '/calc /tex /showtex Integrate x'):
            with self.subTest(prompt=prompt), self.assertRaises(ValueError):
                wltools.wnlc(prompt)

    def test_showtex_does_not_display_equation_for_plot(self) -> None:
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


if __name__ == '__main__':
    unittest.main()
