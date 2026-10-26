project = 'PhDCalc'

extensions = [
    'autoapi.extension',
    'sphinx.ext.autodoc',
    'sphinx.ext.napoleon',
]

autoapi_dirs = ['../src']
autoapi_generate_api_docs = False

napoleon_google_docstring = True
napoleon_numpy_docstring = False

exclude_patterns = ['_build']
html_theme = 'alabaster'
