import alabaster
import ablog

ablog_builder = 'dirhtml'
ablog_website = '_website'

project = 'PyGears'
copyright = '2018, Bogdan Vukobratović'
author = 'Bogdan Vukobratović'

# The short X.Y version
version = ''
# The full version, including alpha/beta/rc tags
release = ''

extensions = [
    'alabaster',
    'ablog'
]

# Add any paths that contain templates here, relative to this directory.
source_suffix = '.rst'
master_doc = 'index'

exclude_patterns = ['_build', 'Thumbs.db', '.DS_Store']

pygments_style = 'sphinx'


html_theme = 'alabaster'
html_title = "PyGears"
html_static_path = ['_static']
html_use_index = True
html_domain_indices = False
html_show_sourcelink = True
# html_favicon = '_static/ablog.ico'

# ABLOG

templates_path = [ablog.get_html_templates_path()]

blog_title = 'PyGears'
blog_baseurl = 'https://bogdanvuk.github.io/pygears/'
# blog_locations = {
#     'Pittsburgh': ('Pittsburgh, PA', 'http://en.wikipedia.org/wiki/Pittsburgh'),
#     'SF': ('San Francisco, CA', 'http://en.wikipedia.org/wiki/San_Francisco'),
#     'Denizli': ('Denizli, Turkey', 'http://en.wikipedia.org/wiki/Denizli'),
# }
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
    '**': ['about.html',
           'postcard.html', 'recentposts.html',
           'tagcloud.html', 'categories.html',
           'archives.html',
           'searchbox.html']
}
html_theme_path = [alabaster.get_path()]
html_theme_options = {
    'travis_button': True,
    'github_user': 'bogdanvuk',
    'github_repo': 'pygears',
    'description': 'PyGears blog',
    # 'logo': 'ablog.png',
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
    (master_doc, 'PyGears.tex', 'PyGears Documentation',
     'Bogdan Vukobratović', 'manual'),
]


# -- Options for manual page output ------------------------------------------

# One entry per manual page. List of tuples
# (source start file, name, description, authors, manual section).
man_pages = [
    (master_doc, 'pygears', 'PyGears Documentation',
     [author], 1)
]


# -- Options for Texinfo output ----------------------------------------------

# Grouping the document tree into Texinfo files. List of tuples
# (source start file, target name, title, author,
#  dir menu entry, description, category)
texinfo_documents = [
    (master_doc, 'PyGears', 'PyGears Documentation',
     author, 'PyGears', 'One line description of project.',
     'Miscellaneous'),
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
