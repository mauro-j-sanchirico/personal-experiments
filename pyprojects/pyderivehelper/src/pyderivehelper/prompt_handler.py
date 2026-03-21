from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class PromptPayload:
    user_prompt: str
    system_prompt: str
    model: str


@dataclass(frozen=True, slots=True)
class PromptResult:
    result: object
    tex: str
