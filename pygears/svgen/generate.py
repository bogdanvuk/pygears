from pygears.core.hier_node import HierVisitorBase
import os
import jinja2
from pygears.util.fileio import save_file


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


class SVGenGenerateVisitor(HierVisitorBase):
    def __init__(self, outdir):
        self.outdir = outdir
        self.template_env = TemplateEnv()

    def SVGenNodeBase(self, module):
        contents = module.get_module(self.template_env)
        if contents:
            save_file(module.get_fn(), self.outdir, contents)


def svgen_generate(top, conf):
    v = SVGenGenerateVisitor(conf['outdir'])
    v.visit(top)

    return top
