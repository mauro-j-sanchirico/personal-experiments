import os
import unittest
from unittest.mock import patch

os.environ.setdefault('OPENAI_PERSONAL_MATH_ASSISTANT', 'test-key')

from pyderivehelper import wltools  # noqa: E402


class ResultReferenceTests(unittest.TestCase):
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
            patch.object(wltools, '_display_result_only') as display_result,
        ):
            result = wltools._wnlc_both_sides_pipeline(
                'Integrate rhs', 'model', True
            )
            self.assertEqual(result, ((3, 3), '3 = 3'))
            self.assertIn('ReleaseHold[lhs]', str(evaluate.call_args.args[0]))
            remember.assert_called_once_with('Integrate[rhs, x]', 3)
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


if __name__ == '__main__':
    unittest.main()
