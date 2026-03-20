from dataclasses import dataclass


@dataclass
class OpenAIModels:
    nano: str = 'gpt-5.4-nano'
    mini: str = 'gpt-5.4-mini'
    full: str = 'gpt-5.4'


def make_openai_api_call(client, model, system_prompt, prompt_template):
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
