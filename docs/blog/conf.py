import datetime
import pkg_resources
import alabaster
import ablog

ablog_builder = 'dirhtml'
ablog_website = '_website'

project = 'PyGears'
this_year = datetime.date.today().year
copyright = f'{this_year}, Bogdan Vukobratovic'
author = 'Bogdan Vukobratović'

version = pkg_resources.get_distribution("pygears").version
release = version

extensions = [
    'sphinx.ext.autodoc',
    'sphinxarg.ext',
    'sphinx_verboser.verboser',
    'sphinx_urlinclude.urlinclude',
    'sphinx_gifplayer.gifplayer',
    'sphinxcontrib.tikz',
    'alabaster',
    'ablog',
    'sphinx_sitemap',
    'sphinx.ext.intersphinx',
    'sphinx.ext.napoleon',
    'bdp.sphinxext.bdpfigure',
]

intersphinx_mapping = {
    'pygears': ('/tools/home/pygears/docs/manual/_build/html/', None)
}
# intersphinx_mapping = {'pygears': ('https://www.pygears.org', None)}
# intersphinx_timeout = 10

site_url = "https://www.pygears.org/blog/"

# Add any paths that contain templates here, relative to this directory.
source_suffix = '.rst'
master_doc = 'index'

exclude_patterns = ['_build', 'Thumbs.db', '.DS_Store']

pygments_style = 'sphinx'

html_theme = 'alabaster'
html_title = "PyGears - HW Design: A Functional Approach"
html_short_title = "PyGears"
html_static_path = ['_static', '../manual/_static']
html_use_index = True
html_baseurl = "https://www.pygears.org"
html_domain_indices = False
html_show_sourcelink = True
html_favicon = '../manual/_static/pygears.ico'

# ABLOG

templates_path = [ablog.get_html_templates_path(), '_templates']


def link_posts_within_category(posts):
    """Link posts after sorting them post by published date."""
    from operator import attrgetter
    posts = filter(attrgetter("order"), posts)
    posts = sorted(posts)
    for p in posts:
        p.prev = p.next = None

    for i in range(0, len(posts) - 1):
        try:
            succ = next(
                p for p in posts[i + 1:] if p.category == posts[i].category)
            posts[i].next = succ
            succ.prev = posts[i]
        except StopIteration:
            posts[i].next = None


ablog.blog.link_posts = link_posts_within_category
blog_title = 'PyGears'
blog_baseurl = 'https://www.pygears.org/'
blog_languages = {
    'en': ('English', None),
}
blog_default_language = 'en'
blog_authors = {
    'Bogdan': (u'Bogdan Vukobratović', 'https://github.com/bogdanvuk'),
}
blog_feed_archives = True
blog_feed_fulltext = True
blog_feed_length = None
disqus_shortname = 'pygears'
disqus_pages = True
# fontawesome_css_file = 'css/font-awesome.css'

# blog_feed_titles = False
# blog_archive_titles = False
# post_auto_excerpt = 1

# THEME

html_style = 'alabaster.css'
html_theme = 'alabaster'
html_sidebars = {
    '**': [
        'custom_about.html', 'postcard.html', 'recentposts.html',
        'tagcloud.html', 'categories.html', 'archives.html', 'searchbox.html'
    ]
}
html_theme_path = [alabaster.get_path()]
html_theme_options = {
    'travis_button': False,
    'github_user': 'bogdanvuk',
    'github_repo': 'pygears',
    'description': 'HW Design: A Functional Approach',
    'logo': 'logo.png',
    'sidebar_width': '230px'
}

# -- Options for HTMLHelp output ---------------------------------------------

# Output file base name for HTML help builder.
htmlhelp_basename = 'PyGearsdoc'

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
    # 'preamble': '',

    # Latex figure (float) alignment
    #
    # 'figure_align': 'htbp',
}

# Grouping the document tree into LaTeX files. List of tuples
# (source start file, target name, title,
#  author, documentclass [howto, manual, or own class]).
latex_documents = [
    (master_doc, 'PyGears.tex', 'PyGears Documentation', 'Bogdan Vukobratović',
     'manual'),
]

# -- Options for manual page output ------------------------------------------

# One entry per manual page. List of tuples
# (source start file, name, description, authors, manual section).
man_pages = [(master_doc, 'pygears', 'PyGears Documentation', [author], 1)]

# -- Options for Texinfo output ----------------------------------------------

# Grouping the document tree into Texinfo files. List of tuples
# (source start file, target name, title, author,
#  dir menu entry, description, category)
texinfo_documents = [
    (master_doc, 'PyGears', 'PyGears Documentation', author, 'PyGears',
     'One line description of project.', 'Miscellaneous'),
]

# -- Options for Epub output -------------------------------------------------

# Bibliographic Dublin Core info.
epub_title = project

# The unique identifier of the text. This can be a ISBN number
# or the project homepage.
#
# epub_identifier = ''

# A unique identification for the text.
#
# epub_uid = ''

# A list of files that should not be packed into the epub file.
epub_exclude_files = ['search.html']

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
