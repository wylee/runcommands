#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import os
import sys
from datetime import date

sys.path.insert(0, os.path.abspath('..'))

from runcommands import __version__  # noqa: E402

# -- General configuration ------------------------------------------------

project = 'RunCommands'
author = 'Wyatt Baldwin'
copyright = '{year} Wyatt Baldwin'.format(year=date.today().year)
github_url = 'https://github.com/wylee/runcommands'

version = __version__
release = version

language = None

master_doc = 'index'

source_suffix = '.rst'

templates_path = ['_templates']

exclude_patterns = ['_build', 'Thumbs.db', '.DS_Store']

pygments_style = 'sphinx'

todo_include_todos = False

extensions = [
    'sphinx.ext.autodoc',
    'sphinx.ext.doctest',
    'sphinx.ext.githubpages',
    'sphinx.ext.intersphinx',
    'sphinx.ext.napoleon',
    'sphinx.ext.viewcode',
]

# reStructuredText options ------------------------------------------------

# This makes `xyz` the same as ``xyz``.
default_role = 'literal'

# This is appended to the bottom of all docs.
rst_epilog = """
.. |project| replace:: {project}
.. |github_url| replace:: {github_url}
""".format_map(locals())

# Options for autodoc extension -------------------------------------------

autodoc_default_flags = ['members']

# Options for intersphinx extension ---------------------------------------

intersphinx_mapping = {
    'python': ('http://docs.python.org/3.3', None),
}

# -- Options for HTML output ----------------------------------------------

html_theme = 'alabaster'

html_theme_options = {
    'description': 'Easily define and run multiple commands',
    'github_user': 'wylee',
    'github_repo': 'runcommands',
    'page_width': '1200px',
    'fixed_sidebar': True,
    'sidebar_width': '300px',
    'extra_nav_links': {
        'Source (GitHub)': github_url,
    },
}

html_sidebars = {
    '**': [
        'about.html',
        'navigation.html',
        'searchbox.html',
    ]
}

html_static_path = []

# -- Options for HTMLHelp output ------------------------------------------

htmlhelp_basename = 'RunCommandsdoc'

# -- Options for LaTeX output ---------------------------------------------

latex_elements = {}

latex_documents = [
    (master_doc, 'RunCommands.tex', 'RunCommands Documentation', 'Wyatt Baldwin', 'manual'),
]

# -- Options for manual page output ---------------------------------------

man_pages = [
    (master_doc, 'runcommands', 'RunCommands Documentation', [author], 1)
]

# -- Options for Texinfo output -------------------------------------------

texinfo_documents = [
    (master_doc, 'RunCommands', 'RunCommands Documentation', author, 'RunCommands',
     'One line description of project.', 'Miscellaneous'),
]
