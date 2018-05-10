from pygears.core.hier_node import HierVisitorBase, HierYielderBase
import os
import jinja2
from pygears.util.fileio import save_file
from pygears import registry


def format_list(list_, pattern):
    return [pattern % s for s in list_]


def keymap(list_, key):
    return [item[key] for item in list_]


def isinput(list_):
    return [item for item in list_ if item["modport"] == "consumer"]


def isoutput(list_):
    return [item for item in list_ if item["modport"] == "producer"]


def startswith(field, s):
    return field.startswith(s)


class TemplateEnv:
    def __init__(self):
        self.basedir = os.path.dirname(__file__)
        self.jenv = jinja2.Environment(
            extensions=['jinja2.ext.do'], trim_blocks=True, lstrip_blocks=True)
        self.jenv.globals.update(
            zip=zip, len=len, int=int, enumerate=enumerate)

        self.jenv.filters['format_list'] = format_list
        self.jenv.filters['keymap'] = keymap
        self.jenv.filters['isinput'] = isinput
        self.jenv.filters['isoutput'] = isoutput
        self.jenv.tests['startswith'] = startswith

        self.snippets = self.load(self.basedir, 'snippet.j2').module

    def load(self, tmplt_dir, tmplt_fn):
        self.jenv.loader = jinja2.FileSystemLoader([self.basedir, tmplt_dir])
        return self.jenv.get_template(tmplt_fn)

    def render_local(self, fn, tmplt_fn, context):
        return self.render(os.path.dirname(fn), tmplt_fn, context)

    def render(self, tmplt_dir, tmplt_fn, context):
        return self.load(tmplt_dir, tmplt_fn).render(context)


class SVGenGenerateVisitor(HierYielderBase):
    def __init__(self):
        self.template_env = TemplateEnv()
        self.svgen_map = registry('SVGenMap')

    def RTLNode(self, node):
        svgen = self.svgen_map.get(node, None)
        if svgen is not None:
            contents = svgen.get_module(self.template_env)
            yield svgen, contents

        yield from super().HierNode(node)


def svgen_module(node):
    v = SVGenGenerateVisitor()
    svgen, contents = next(v.visit(node))
    return contents


def svgen_yield(top):
    v = SVGenGenerateVisitor()
    for svgen, contents in v.visit(top):
        if contents:
            yield svgen, contents


def svgen_generate(top, conf):
    v = SVGenGenerateVisitor()
    for svgen, contents in v.visit(top):
        if contents:
            if isinstance(contents, (tuple, list)):
                print(svgen.sv_file_name)
                for fn, c in zip(svgen.sv_file_name, contents):
                    save_file(fn, conf['outdir'], c)
            else:
                save_file(svgen.sv_file_name, conf['outdir'], contents)

    return top
