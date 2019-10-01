from docutils import nodes
from sphinx.util.docutils import SphinxDirective
from docutils.parsers.rst import directives
from docutils.statemachine import StringList


class PgExampleDirective(SphinxDirective):
    required_arguments = 1
    optional_arguments = 0

    option_spec = {
        'lines': directives.unchanged,
        'emphasize-lines': directives.unchanged,
        'sections': directives.unchanged
    }

    def make_tryme(self):
        tryme_node = nodes.section()
        self.state.nested_parse(
            StringList([f'.. tryme:: {self.arguments[0]}.py']), 0, tryme_node)

        return tryme_node.children

    def make_include(self):
        include_node = nodes.section()
        self.state.nested_parse(
            StringList([
                f'.. literalinclude:: {self.arguments[0]}.py\n',
                f'    :lines: {self.options["lines"]}\n'
                if 'lines' in self.options else '',
                f'    :emphasize-lines: {self.options["emphasize-lines"]}'
                if 'emphasize-lines' in self.options else '',
            ]), 0, include_node)

        return include_node.children

    def make_wavedrom(self):
        wavedrom_node = nodes.section()
        self.state.nested_parse(
            StringList([f'.. wavedrom:: {self.arguments[0]}.json']), 0,
            wavedrom_node)

        return wavedrom_node.children

    def run(self):
        if 'sections' not in self.options:
            self.options['sections'] = ['tryme', 'include', 'wavedrom']

        children = []
        for section in self.options['sections']:
            children.extend(getattr(self, f'make_{section}')())

        return children


def setup(app):
    directives.register_directive('pg-example', PgExampleDirective)

    return {'version': '0.1'}
