from dataclasses import dataclass


@dataclass
class OpenAIModels:
    nano: str = 'gpt-5.4-nano'
    mini: str = 'gpt-5.4-mini'
    full: str = 'gpt-5.4'
