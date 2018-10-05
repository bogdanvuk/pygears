import pkg_resources
import datetime
import os
import sys
sys.path.insert(0, os.path.abspath('../..'))
sys.path.insert(0, os.path.abspath('../../examples/echo'))

print(os.path.abspath('../../pygears'))

# -- Project information -----------------------------------------------------

project = 'PyGears'
this_year = datetime.date.today().year
copyright = f'{this_year}, Bogdan Vukobratovic'
author = 'Bogdan Vukobratovic'

version = pkg_resources.get_distribution("pygears").version
release = version

# -- General configuration ---------------------------------------------------

# If your documentation needs a minimal Sphinx version, state it here.
#
# needs_sphinx = '1.0'

# Add any Sphinx extension module names here, as strings. They can be
# extensions coming with Sphinx (named 'sphinx.ext.*') or your custom
# ones.
extensions = [
    'sphinx_verboser.verboser', 'sphinxarg.ext', 'sphinx.ext.autodoc',
    'sphinx.ext.githubpages', 'sphinxcontrib.tikz', 'sphinxcontrib.wavedrom',
    'bdp.sphinxext.bdpfigure', 'sphinx.ext.napoleon'
]
autodoc_default_options = {
    'show-inheritance': None,
    'members': None,
    'special-members': None
}
autoclass_content = "class"
add_module_names = False

offline_skin_js_path = r"default.js"
offline_wavedrom_js_path = r"wavedrom.js"

# Taken from: https://stackoverflow.com/questions/46279030/how-can-i-prevent-sphinx-from-listing-object-as-a-base-class
# ClassDocumenter.add_directive_header uses ClassDocumenter.add_line to write
#   the class documentation. We'll monkeypatch the add_line method and
#   intercept lines that begin with "Bases:". In order to minimize the risk of
#   accidentally intercepting a wrong line, we'll apply this patch inside of
#   the add_directive_header method.

from sphinx.ext.autodoc import ClassDocumenter, _


def autodoc_skip_member(app, what, name, obj, skip, options):
    exclusions = (
        '__weakref__',  # special-members
        '__new__',
        '__str__',
        '__repr__',  # undoc-members
    )
    exclude = name in exclusions
    return skip or exclude


def setup(app):
    app.connect('autodoc-skip-member', autodoc_skip_member)


add_line = ClassDocumenter.add_line
line_to_delete = _(u'Bases: %s') % u':class:`object`'


def add_line_no_object_base(self, text, *args, **kwargs):
    if text.strip() == line_to_delete:
        return

    add_line(self, text, *args, **kwargs)


add_directive_header = ClassDocumenter.add_directive_header


def add_directive_header_no_object_base(self, *args, **kwargs):
    self.add_line = add_line_no_object_base.__get__(self)

    result = add_directive_header(self, *args, **kwargs)

    del self.add_line

    return result


ClassDocumenter.add_directive_header = add_directive_header_no_object_base

# Add any paths that contain templates here, relative to this directory.
templates_path = ['_templates']

# The suffix(es) of source filenames.
# You can specify multiple suffix as a list of string:
#
# source_suffix = ['.rst', '.md']
source_suffix = '.rst'

# The master toctree document.
master_doc = 'index'

# The language for content autogenerated by Sphinx. Refer to documentation
# for a list of supported languages.
#
# This is also used if you do content translation via gettext catalogs.
# Usually you set "language" from the command line for these cases.
language = None

# List of patterns, relative to source directory, that match files and
# directories to ignore when looking for source files.
# This pattern also affects html_static_path and html_extra_path .
exclude_patterns = ['_build', 'Thumbs.db', '.DS_Store']

# The name of the Pygments (syntax highlighting) style to use.
pygments_style = 'sphinx'

# -- Options for HTML output -------------------------------------------------

# The theme to use for HTML and HTML Help pages.  See the documentation for
# a list of builtin themes.
#
html_theme = 'alabaster'

# Theme options are theme-specific and customize the look and feel of a theme
# further.  For a list of options available for each theme, see the
# documentation.
#
html_theme_options = {
    'travis_button': False,
    'github_user': 'bogdanvuk',
    'github_repo': 'pygears',
    'github_banner': True,
    'description': 'HW design - a functional approach',
    # 'logo': 'ablog.png',
}

# Add any paths that contain custom static files (such as style sheets) here,
# relative to this directory. They are copied after the builtin static files,
# so a file named "default.css" will overwrite the builtin "default.css".
html_static_path = ['_static']

html_sidebars = {
    '**': ['about.html', 'globaltoc.html', 'blog_link.html', 'searchbox.html']
    }

# -- Options for HTMLHelp output ---------------------------------------------

# Output file base name for HTML help builder.
htmlhelp_basename = 'pygearsdoc'

# -- Options for LaTeX output ------------------------------------------------

latex_elements = {
    # The paper size ('letterpaper' or 'a4paper').
    #
    # 'papersize': 'letterpaper',

    # The font size ('10pt', '11pt' or '12pt').
    #
    # 'pointsize': '10pt',

    # Additional stuff for the LaTeX preamble.
    #
    'preamble': r'''
    ''',

    # Latex figure (float) alignment
    #
    # 'figure_align': 'htbp',
}

# Grouping the document tree into LaTeX files. List of tuples
# (source start file, target name, title,
#  author, documentclass [howto, manual, or own class]).
latex_documents = [
    (master_doc, 'pygears.tex', 'pygears Documentation', 'Bogdan Vukobratovic',
     'manual'),
]

# -- Options for manual page output ------------------------------------------

# One entry per manual page. List of tuples
# (source start file, name, description, authors, manual section).
man_pages = [(master_doc, 'pygears', 'pygears Documentation', [author], 1)]

# -- Options for Texinfo output ----------------------------------------------

# Grouping the document tree into Texinfo files. List of tuples
# (source start file, target name, title, author,
#  dir menu entry, description, category)
texinfo_documents = [
    (master_doc, 'pygears', 'pygears Documentation', author, 'pygears',
     'One line description of project.', 'Miscellaneous'),
]

# -- Extension configuration -------------------------------------------------

# Gear takes five parameters:
# 1. Number of cogs
# 2. Radius of center
# 3. Radius of the gear
# 4. Width of the cog
# 5. Slope of the cog
# 6. Gear node
# 7. Gear text

tikz_latex_preamble = r'''

\newcommand{\gear}[7]{%

node {#7}

\foreach \i in {1,...,#1} {%
  [rotate=(\i-1)*360/#1]  (0:#2)  arc (0:#4:#2) {[rounded corners=1.5pt]
            -- (#4+#5:#3)  arc (#4+#5:360/#1-#5:#3)} --  (360/#1:#2)
}}

\tikzset{
  pics/mynode/.style args={#1}{
     code={
       \draw[thick] \gear{10}{2}{2.4}{14}{1}{prod}{#1};
     }
  }
}
'''
