from collections.abc import Callable
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch

import pytest
from phdcalc import agents, config_file_management, openai_api


def test_api_call_sends_prompts_and_strips_response() -> None:
    client = Mock()
    client.responses.create.return_value = SimpleNamespace(output_text='  result\n')
    assert openai_api.make_openai_api_call(
        client, 'model', 'system instructions', 'user prompt'
    ) == 'result'
    client.responses.create.assert_called_once_with(
        model='model',
        temperature=0,
        input=[
            {'role': 'system', 'content': 'system instructions'},
            {'role': 'user', 'content': 'user prompt'},
        ],
    )


def test_agent_sends_templated_prompt_to_api() -> None:
    client = Mock()
    agent = agents.WolframCodeGenerator(client, 'model')
    with patch.object(agents, 'make_openai_api_call', return_value='result') as call:
        assert agent.call('square x') == 'result'
    assert call.call_args.args[:3] == (
        client, 'model', agents.SystemPrompts.wolfram_code_generator
    )
    assert 'square x' in call.call_args.args[3]


@pytest.mark.parametrize(
    'agent_type',
    [
        agents.WolframCodeSanitizer,
        agents.WolframCodeFixer,
        agents.WolframPlotSummarizer,
        agents.TeXGenerator,
        agents.TeXCodeFixer,
    ],
)
def test_agent_templates_include_user_input(
    agent_type: Callable[[object, str], agents.Agent],
) -> None:
    agent = agent_type(Mock(), 'model')
    assert 'sample input' in agent.template_prompt('sample input')
    assert agent.system_prompt


def test_base_agent_requires_a_prompt_template() -> None:
    agent = agents.Agent(Mock(), 'model', 'system')
    with pytest.raises(NotImplementedError):
        agent.template_prompt('prompt')


def test_config_rejects_non_mapping_yaml(tmp_path: Path) -> None:
    config_path = tmp_path / 'config.yaml'
    config_path.write_text('- item\n', encoding='utf-8')
    with patch.object(config_file_management, '_CONFIG_PATH', config_path):
        with pytest.raises(ValueError, match='Invalid config file'):
            config_file_management.load_config()
