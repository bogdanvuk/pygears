from pygears.core.hier_node import HierVisitorBase, HierYielderBase
import os
import jinja2
from pygears.util.fileio import save_file
from pygears import registry
from pygears.svgen.util import svgen_typedef
from pygears.rtl.inst import RTLNodeDesign
from pygears.typing import bitw


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
        self.templates = {}
        self.jenv = jinja2.Environment(
            extensions=['jinja2.ext.do'], trim_blocks=True, lstrip_blocks=True)
        self.jenv.globals.update(
            zip=zip,
            len=len,
            int=int,
            bitw=bitw,
            enumerate=enumerate,
            svgen_typedef=svgen_typedef)

        self.jenv.filters['format_list'] = format_list
        self.jenv.filters['keymap'] = keymap
        self.jenv.filters['isinput'] = isinput
        self.jenv.filters['isoutput'] = isoutput
        self.jenv.tests['startswith'] = startswith

        self.snippets = self.load(self.basedir, 'snippet.j2').module

    def load(self, tmplt_dir, tmplt_fn):
        key = os.path.join(self.basedir, tmplt_dir, tmplt_fn)
        if key not in self.templates:
            self.jenv.loader = jinja2.FileSystemLoader([self.basedir, tmplt_dir])
            template = self.jenv.get_template(tmplt_fn)
            self.templates[key] = template

        return self.templates[key]

    def render_local(self, fn, tmplt_fn, context):
        return self.render(os.path.dirname(fn), tmplt_fn, context)

    def render(self, tmplt_dir, tmplt_fn, context):
        return self.load(tmplt_dir, tmplt_fn).render(context)


class SVGenGenerateVisitor(HierYielderBase):
    def __init__(self, top, wrapper=False):
        self.template_env = TemplateEnv()
        self.svgen_map = registry('SVGenMap')
        self.wrapper = wrapper
        self.top = top

    def RTLNode(self, node):
        svgen = self.svgen_map.get(node, None)
        if svgen is not None:
            contents = svgen.get_module(self.template_env)
            # print(f'Generating {svgen.sv_file_name}')
            yield svgen.sv_file_name, contents

            if (self.wrapper) and (node == self.top):
                yield f'wrap_{svgen.sv_file_name}', svgen.get_synth_wrap(
                    self.template_env)


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
    v = SVGenGenerateVisitor(top, conf.get('wrapper', False))
    for file_names, contents in v.visit(top):
        if contents:
            if isinstance(contents, (tuple, list)):
                for fn, c in zip(file_names, contents):
                    save_file(fn, conf['outdir'], c)
            else:
                save_file(file_names, conf['outdir'], contents)

    return top
