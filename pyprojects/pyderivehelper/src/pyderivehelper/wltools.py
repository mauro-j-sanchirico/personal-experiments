import os
import re

import matplotlib.image as mpimg
import matplotlib.pyplot as plt
from dotenv import load_dotenv
from IPython.display import Markdown, Math, display
from openai import OpenAI
from wolframclient.evaluation import WolframLanguageSession
from wolframclient.language import wl

from pyderivehelper.config_openai import OpenAIModels
from pyderivehelper.config_wl import _FAILED_RESULT
from pyderivehelper.prompts import (
    SystemPrompts,
    populate_wolfram_code_generator_prompt_template,
)

# Load environment variables
load_dotenv()

# Start the Wolfram Language session
ws = WolframLanguageSession()

# Create the OpenAI client
math_assistant_client = OpenAI(
    api_key=os.environ['OPENAI_PERSONAL_MATH_ASSISTANT']
)


def print_tex(expr):
    """Prints an raw expression in rendered TeX."""
    display(Math(expr))


def print_wexpr(expr):
    """Prints a Wolfram expression in rendered TeX."""
    tex_expr = ws.evaluate(wl.ToString(wl.TeXForm(expr)))
    display(Math(tex_expr))


def print_wresult(expr):
    """Evaluates Wolfram expression and renders the result via TeX."""
    tex_expr = ws.evaluate(wl.ToString(wl.TeXForm(ws.evaluate(expr))))
    display(Math(tex_expr))


def print_wresult_tex(expr):
    """Evaluates a Wolfram expression and print the result in raw TeX form."""
    tex_expr = ws.evaluate(wl.ToString(wl.TeXForm(ws.evaluate(expr))))
    print(tex_expr)


def check_syntax(expr):
    valid_syntax_check_str = f'SyntaxQ["{expr}"]'
    syntax_check_result = str(ws.evaluate(valid_syntax_check_str))
    if _FAILED_RESULT in syntax_check_result:
        return False
    return True


def wplot(filename, command):
    export_expr = f'Export["{filename}", {command}]'
    ws.evaluate(export_expr)
    img = mpimg.imread(filename)
    plt.imshow(img)
    plt.show()
    plt.axis('off')


def wc(expr):
    """Evaluates an expression, stores, and prints the result"""
    result = ws.evaluate(expr)
    save_expr_str = f'rrr = {expr}'
    ws.evaluate(save_expr_str)
    print_wresult(ws.evaluate('rrr'))
    return result


def wnlp(prompt, model=OpenAIModels.mini):
    # Generate code
    print('Generating Wolfram Language code...')
    response_str = generate_wolfram_language(prompt, model)
    display(Markdown('\n**Wolfram Code**:\n'))
    display(Markdown(f'```wolfram\n{response_str}\n```'))
    # TODO: Check if the response is valid Wolfram Language code

    # TODO: Check if there is a plot and call plot if there is

    # Evaluate the result and display
    display(Markdown('\n**Raw Evaluated Result**:\n'))
    result = ws.evaluate(response_str)
    display(Markdown(f'```plaintext\n{result!s}\n```'))

    # Render as Math
    display(Markdown('\n**Rendered Evaluated Result**:\n'))
    tex_str = ws.evaluate(wl.ToString(wl.TeXForm(result)))
    # Fix the way Wolfram exports hypergeometric functions
    tex_str = re.sub(r' _(\d+[A-Za-z])', r' {}_\1', tex_str)
    display(Math(tex_str))

    # Print raw TeX for copy-pasting
    display(Markdown('\n**Raw TeX**:\n'))
    tex_str = print_wresult_tex(result)
    display(Markdown(f'```tex\n{tex_str}\n```'))

    return result


def generate_wolfram_language(prompt, model):
    prompt_template = populate_wolfram_code_generator_prompt_template(prompt)
    response = math_assistant_client.responses.create(
        model=model,
        temperature=0,
        input=[
            {
                'role': 'system',
                'content': SystemPrompts.wolfram_code_generator,
            },
            {
                'role': 'user',
                'content': prompt_template,
            },
        ],
    )
    response_str: str = response.output_text.strip()
    return response_str
