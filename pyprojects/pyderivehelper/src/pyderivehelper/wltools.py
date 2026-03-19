import os
import re
import tempfile

import matplotlib.image as mpimg
import matplotlib.pyplot as plt
from dotenv import load_dotenv
from IPython.display import Markdown, Math, display
from openai import OpenAI
from wolframclient.evaluation import WolframLanguageSession
from wolframclient.language import wl

from pyderivehelper.config_openai import OpenAIModels
from pyderivehelper.config_wl import PlotCommands, SyntaxCheckResults
from pyderivehelper.prompts import (
    SystemPrompts,
    populate_wolfram_code_generator_prompt_template,
    populate_wolfram_code_sanitizer_prompt_template,
    populate_wolfram_plot_summarizer_prompt_template,
)

# =============================================================================
# Session boiler plate to start Wolfram Language session and OpenAI client
# =============================================================================
load_dotenv()
ws = WolframLanguageSession()
math_assistant_client = OpenAI(
    api_key=os.environ['OPENAI_PERSONAL_MATH_ASSISTANT']
)


# =============================================================================
# User convenience functions for displaying Wolfram Language results in Jupyter
# notebooks
# =============================================================================
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


# =============================================================================
# I/O validation functions
# =============================================================================


def check_syntax(expr):
    valid_syntax_check_str = f'SyntaxQ["{expr}"]'
    syntax_check_result = str(ws.evaluate(valid_syntax_check_str))
    if SyntaxCheckResults.FAILED_RESULT in syntax_check_result:
        return False
    return True


def check_contains_plot_code(expr, plot_commands=PlotCommands.commands):
    """Returns True when expr contains any plot command word."""
    for command in plot_commands:
        if re.search(rf'\b{re.escape(command)}\b', expr):
            return True
    return False


# ============================================================================
# Main user-facing functions for generating and using Wolfram Language code
# ============================================================================


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

    # Sanitize the generated code
    print('Sanitizing generated code...')
    response_str = sanitize_wolfram_language_code(
        response_str, OpenAIModels.mini
    )

    # Check syntax before evaluating
    print('Checking syntax...')
    if not check_syntax(response_str):
        print('Generated response is not valid Wolfram Language code:')
        display(Markdown('\n**Invalid Wolfram Code**:\n'))
        display(Markdown(f'```wolfram\n{response_str}\n```'))
        return None

    # Display the generated code
    display(Markdown('\n**Wolfram Code**:\n'))
    display(Markdown(f'```wolfram\n{response_str}\n```'))

    # Detect if the code contains plot commands and render the plot if it does
    if check_contains_plot_code(response_str):
        print('Detected plot code. Rendering plot...')
        os.makedirs('images', exist_ok=True)
        human_readable_filename = summarize_plot_code_to_filename(
            response_str, OpenAIModels.mini
        )
        prefix = human_readable_filename + '_'
        filename = ''
        with tempfile.NamedTemporaryFile(
            prefix=prefix,
            dir='images',
            suffix='.png',
            delete=False,
        ) as temp_file:
            filename = temp_file.name
            temp_file.close()  # Close the file so that Wolfram can write to it
        relative_path = os.path.relpath(filename, os.getcwd())
        relative_path = relative_path.replace(
            '\\', '/'
        )  # Handle Windows paths
        print(relative_path)
        wplot(relative_path, response_str)
        return None

    # Evaluate the result
    result = ws.evaluate(response_str)

    # Get TeX representation
    tex_str = ws.evaluate(wl.ToString(wl.TeXForm(result)))

    # Clean TeX representation
    # Fix the way Wolfram exports hypergeometric functions
    cleaned_tex_str = re.sub(r' _(\d+[A-Za-z])', r' {}_\1', tex_str)

    # Display the raw evaluated result
    display(Markdown('\n**Raw Evaluated Result**:\n'))
    display(Markdown(f'```plaintext\n{result!s}\n```'))

    # Display the rendered TeX result
    display(Markdown('\n**Rendered Evaluated Result**:\n'))
    display(Math(cleaned_tex_str))

    # Print raw TeX source code for copy-pasting
    display(Markdown('\n**Raw TeX**:\n'))
    display(Markdown(f'```tex\n{cleaned_tex_str}\n```'))

    return result, cleaned_tex_str


def generate_wolfram_language(prompt, model):
    templated_prompt = populate_wolfram_code_generator_prompt_template(prompt)
    code = make_openai_api_call(
        model, SystemPrompts.wolfram_code_generator, templated_prompt
    )
    return code


def sanitize_wolfram_language_code(code, model):
    templated_prompt = populate_wolfram_code_sanitizer_prompt_template(code)
    sanitized_code = make_openai_api_call(
        model, SystemPrompts.wolfram_code_sanitizer, templated_prompt
    )
    return sanitized_code


def summarize_plot_code_to_filename(code, model):
    templated_prompt = populate_wolfram_plot_summarizer_prompt_template(code)
    filename = make_openai_api_call(
        model, SystemPrompts.wolfram_plot_summarizer, templated_prompt
    )
    return filename


def make_openai_api_call(model, system_prompt, prompt_template):
    response = math_assistant_client.responses.create(
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
