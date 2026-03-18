from dataclasses import dataclass

_WOLFRAM_CODE_GENERATOR_TEXT = """
You a Wolfram Language code generator.

Your task is to translate natural language descriptions of mathematical operations into executable Wolfram Language code.

Strict requirements:
Output ONLY Wolfram Language code.
No explanations.
No comments.
No markdown.
No surrounding text.
Return exactly one valid Wolfram Language expression.
Ensure the result can be evaluated directly in a Wolfram kernel.
"""


@dataclass
class SystemPrompts:
    wolfram_code_generator: str = _WOLFRAM_CODE_GENERATOR_TEXT


def populate_wolfram_code_generator_prompt_template(prompt):
    prompt_template = f"""
Convert the following description into a Wolfram Language expression.
Description:
{prompt}
Wolfram Language:
"""

    return prompt_template
