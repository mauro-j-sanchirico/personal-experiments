from unittest.mock import Mock, patch

import pytest
from phdcalc import wltools


@pytest.mark.parametrize(
    ('validation_results', 'expected'),
    [([True], 'original'), ([False, True], 'repaired'), ([False] * 4, '')],
)
def test_wolfram_validation_retries(
    validation_results: list[bool], expected: str
) -> None:
    fixer = Mock()
    fixer.call.return_value = 'repaired'
    with patch.object(
        wltools, 'validate_wolfram_code', side_effect=validation_results
    ) as validate:
        assert wltools._validate_or_fix_wolfram_code('original', fixer) == expected
    assert validate.call_count == len(validation_results)
    if len(validation_results) == 1:
        fixer.call.assert_not_called()
    else:
        fixer.call.assert_any_call('original')


@pytest.mark.parametrize(
    ('validation_results', 'expected'),
    [([True], r'x^2'), ([False, True], r'\frac{x}{2}'), ([False] * 4, '')],
)
def test_tex_validation_retries(
    validation_results: list[bool], expected: str
) -> None:
    fixer = Mock()
    fixer.call.return_value = r'\frac{x}{2}'
    with patch.object(wltools, 'validate_tex_code', side_effect=validation_results):
        assert wltools._validate_or_fix_tex_code(r'x^2', fixer) == expected


def test_wolfram_generation_sanitizes_before_validation() -> None:
    with (
        patch.object(wltools.WolframCodeGenerator, 'call', return_value='raw')
        as generate,
        patch.object(wltools.WolframCodeSanitizer, 'call', return_value='clean')
        as sanitize,
        patch.object(wltools, '_validate_or_fix_wolfram_code', return_value='valid')
        as validate,
    ):
        assert wltools._generate_validated_wolfram_code('square x', 'model') == (
            'valid', 'raw'
        )
    generate.assert_called_once_with('square x')
    sanitize.assert_called_once_with('raw')
    assert validate.call_args.args[0] == 'clean'


def test_user_code_is_sanitized_and_validated() -> None:
    with (
        patch.object(wltools.WolframCodeSanitizer, 'call', return_value='clean')
        as sanitize,
        patch.object(wltools, '_validate_or_fix_wolfram_code', return_value='valid')
        as validate,
    ):
        assert wltools._validate_user_wolfram_code('input', 'model') == 'valid'
    sanitize.assert_called_once_with('input')
    assert validate.call_args.args[0] == 'clean'


def test_tex_generation_validates_generated_expression() -> None:
    with (
        patch.object(wltools.TeXGenerator, 'call', return_value='raw') as generate,
        patch.object(wltools, '_validate_or_fix_tex_code', return_value='valid')
        as validate,
    ):
        assert wltools._generate_validated_tex_code('fraction', 'model') == (
            'valid', 'raw'
        )
    generate.assert_called_once_with('fraction')
    assert validate.call_args.args[0] == 'raw'


def test_tex_validation_reports_parser_failure() -> None:
    with patch.object(wltools.LatexWalker, 'get_latex_nodes', side_effect=ValueError):
        assert not wltools.validate_tex_code(r'\bad')
    assert wltools.validate_tex_code(r'x^2')


def test_wolfram_validation_accepts_successful_evaluation() -> None:
    with patch.object(wltools.ws, 'evaluate', return_value=2):
        assert wltools.validate_wolfram_code('1 + 1')
