import os

master_doc = 'index'
project = 'sanest'
copyright = 'wouter bolsterlee (@wbolster)'

extensions = [
    'sphinx.ext.autodoc',
]

if 'READTHEDOCS' not in os.environ:
    import sphinx_rtd_theme
    html_theme = 'sphinx_rtd_theme'
    html_theme_path = [sphinx_rtd_theme.get_html_theme_path()]
