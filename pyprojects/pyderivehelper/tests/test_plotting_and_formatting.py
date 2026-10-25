import logging
from pathlib import Path
from unittest.mock import patch

import pytest
from PIL import Image
from pyderivehelper import wltools


def test_plot_file_uses_configured_directory_and_extension(tmp_path: Path) -> None:
    with patch.object(wltools, '_PLOT_DIRECTORY', str(tmp_path)):
        filename = wltools._make_image_file('sample_plot')
    image_path = Path(filename)
    assert image_path.parent == tmp_path
    assert image_path.name.startswith('sample_plot_')
    assert image_path.suffix == wltools._PLOT_EXTENSION
    assert image_path.is_file()


def test_plot_export_displays_saved_image(tmp_path: Path) -> None:
    image_path = tmp_path / 'plot.png'
    Image.new('RGB', (1, 1)).save(image_path)
    with (
        patch.object(wltools.ws, 'evaluate') as evaluate,
        patch.object(wltools, 'display') as display,
    ):
        wltools.wplot(str(image_path), 'Plot[x, {x, 0, 1}]')
    assert str(image_path) in evaluate.call_args.args[0]
    assert isinstance(display.call_args.args[0], Image.Image)


def test_generated_plot_uses_summary_as_filename() -> None:
    with (
        patch.object(wltools.WolframPlotSummarizer, 'call', return_value='line_plot')
        as summarize,
        patch.object(wltools, '_make_image_file', return_value='images/line_plot.png')
        as make_file,
        patch.object(wltools, '_to_relative_path', return_value='images/line_plot.png'),
        patch.object(wltools, 'wplot') as plot,
    ):
        wltools._generate_plot_from_wolfram_code('Plot[x, {x, 0, 1}]')
    summarize.assert_called_once_with('Plot[x, {x, 0, 1}]')
    make_file.assert_called_once_with('line_plot')
    plot.assert_called_once_with('images/line_plot.png', 'Plot[x, {x, 0, 1}]')


def test_tex_cleanup_handles_wolfram_output() -> None:
    with patch.object(
        wltools.ws, 'evaluate', return_value=r'\fbox{$x$} + F _2a'
    ):
        assert wltools._extract_mathjax_safe_tex(2) == r'\boxed{x} + F {}_2a'


@pytest.mark.parametrize(
    ('is_integral', 'expected'),
    [(True, 'input = x + C'), (False, 'input = x')],
)
def test_equation_adds_constant_only_for_indefinite_integral(
    is_integral: bool, expected: str
) -> None:
    with patch.object(
        wltools.ws, 'evaluate', side_effect=[is_integral, 'input']
    ):
        assert wltools._build_equation_tex('x', unwrap_full_simplify=True) == expected


def test_relative_plot_path_uses_forward_slashes(tmp_path: Path) -> None:
    filename = tmp_path / 'plot.png'
    with patch.object(wltools.os, 'getcwd', return_value=str(tmp_path.parent)):
        assert wltools._to_relative_path(str(filename)) == (
            f'{tmp_path.name}/plot.png'
        )


def test_display_helpers_show_expected_content() -> None:
    with patch.object(wltools, 'display') as display:
        wltools._display_help_message()
        wltools._handle_wolfram_validation_error('bad[]')
        wltools._handle_tex_validation_error(r'\bad')
        wltools._display_generated_code('x + 1')
        wltools._display_generated_tex(r'x^2')
        wltools._default_display_results(2, '1+1=2')
        wltools._display_result_only('1+1=2')
    output = '\n'.join(str(call.args[0].data) for call in display.call_args_list)
    assert '/calc' in output
    assert 'Unfixable Wolfram Code' in output
    assert 'Unfixable TeX' in output
    assert 'bad[]' in output
    assert '$$\\Large 1+1=2$$' in output


def test_print_tex_and_wolfram_result() -> None:
    with (
        patch.object(wltools.ws, 'evaluate', side_effect=[2, r'x^2']),
        patch.object(wltools, 'display') as display,
    ):
        wltools.print_tex(r'x^2')
        wltools.print_wresult_tex('x * x')
    assert display.call_args_list[0].args[0].data == r'x^2'
    assert r'x^2' in display.call_args_list[1].args[0].data


def test_log_level_updates_module_and_agent_loggers() -> None:
    agents_logger = logging.getLogger('pyderivehelper.agents')
    with (
        patch.object(wltools.logger, 'setLevel') as set_tools_level,
        patch.object(agents_logger, 'setLevel') as set_agents_level,
    ):
        wltools.set_log_level('debug')
    set_tools_level.assert_called_once_with('DEBUG')
    set_agents_level.assert_called_once_with('DEBUG')
