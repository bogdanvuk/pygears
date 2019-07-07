import os
import shutil
from docutils import nodes
from sphinx.util.docutils import SphinxDirective
from docutils.parsers.rst import directives


class tryme(nodes.General, nodes.Element):
    pass


class TryMeDirective(SphinxDirective):
    required_arguments = 1
    optional_arguments = 0

    # has_content = True

    def run(self):
        node = tryme(self.arguments[0])
        self.state.nested_parse(self.content, self.content_offset, node)
        return [node]


def visit_tryme_node(self, node):
    curdir = os.path.dirname(self.builder.current_docname)

    rel_file_name = node.rawsource
    file_name = os.path.join(curdir, rel_file_name)
    shutil.copyfile(file_name, os.path.join(self.builder.outdir, file_name))

    self.body.append(self.starttag(node, 'div'))
    self.body.append(f'''
      <link href="/_static/css/fontello.css" type="text/css" rel="stylesheet"/>
      <button id="cmdrun" class="btn-run cls-tryme" style="font-size:16px; font-weight:bold;" onClick="window.open(\'/live.html?file={file_name}\', \'_blank\');" title="Run this example on PyGears LIVE!"><i class="icon-cog-alt"></i> Try Me!</button>'''
                     )


def depart_tryme_node(self, node):
    self.body.append('</div>\n')


def setup(app):
    directives.register_directive('tryme', TryMeDirective)
    app.add_node(tryme, html=(visit_tryme_node, depart_tryme_node))

    return {'version': '0.1'}
