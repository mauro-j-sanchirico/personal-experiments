import matplotlib.image as mpimg
import matplotlib.pyplot as plt
from IPython.display import Math, display
from wolframclient.evaluation import WolframLanguageSession
from wolframclient.language import wl

from pyderivehelper.wlconfig import _FAILED_RESULT

ws = WolframLanguageSession()


def print_tex(expr):
    """Prints an expression in latex"""
    display(Math(expr))


def print_wexpr(expr):
    """Prints a wolfram language result in latex"""
    tex_expr = ws.evaluate(wl.ToString(wl.TeXForm(expr)))
    display(Math(tex_expr))


def print_wresult(expr):
    """Prints a wolfram language expression in latex"""
    tex_expr = ws.evaluate(wl.ToString(wl.TeXForm(ws.evaluate(expr))))
    display(Math(tex_expr))


def print_wresult_tex(expr):
    """Prints a wolfram language expression in latex"""
    tex_expr = ws.evaluate(wl.ToString(wl.TeXForm(ws.evaluate(expr))))
    print(tex_expr)


def wc(expr):
    """Evaluates an expression, stores, and prints the result"""
    result = ws.evaluate(expr)
    save_expr_str = f'rrr = {expr}'
    ws.evaluate(save_expr_str)
    print_wresult(ws.evaluate('rrr'))
    return result


def wplot(filename, command):
    export_expr = f'Export["{filename}", {command}]'
    ws.evaluate(export_expr)
    img = mpimg.imread(filename)
    plt.imshow(img)
    plt.show()
    plt.axis('off')


def check_syntax(expr):
    valid_syntax_check_str = f'SyntaxQ["{expr}"]'
    syntax_check_result = str(ws.evaluate(valid_syntax_check_str))
    if syntax_check_result == _FAILED_RESULT:
        return False
    return True
