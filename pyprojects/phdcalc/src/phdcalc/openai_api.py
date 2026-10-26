"""Define model aliases and a shared OpenAI Responses API helper."""

from dataclasses import dataclass

from openai import OpenAI


@dataclass(frozen=True)
class OpenAIModels:
    """Model identifiers used by the package's generation and repair agents."""

    nano: str = 'gpt-5.4-nano'
    mini: str = 'gpt-5.4-mini'
    full: str = 'gpt-5.4'


def make_openai_api_call(
    client: OpenAI,
    model: str,
    system_prompt: str,
    prompt_template: str,
) -> str:
    """Send system and user prompts and return stripped response text."""
    response = client.responses.create(
        model=model,
        temperature=0,
        input=[
            {
                'role': 'system',
                'content': system_prompt,
            },
            {
                'role': 'user',
                'content': prompt_template,
            },
        ],
    )
    response_str: str = response.output_text.strip()
    return response_str
