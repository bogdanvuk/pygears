import os
from pygears.core.hier_node import HierYielderBase
from pygears.util.fileio import save_file
from pygears.hdl.templenv import TemplateEnv
from pygears import registry
from .util import svgen_typedef


class SVTemplateEnv(TemplateEnv):
    lang = 'sv'

    def __init__(self):
        super().__init__(basedir=os.path.dirname(__file__))

        self.jenv.globals.update(svgen_typedef=svgen_typedef)

        self.snippets = self.load(self.basedir, 'snippet.j2').module


class SVGenGenerateVisitor(HierYielderBase):
    def __init__(self, top, outdir, wrapper=False):
        self.template_env = SVTemplateEnv()
        self.svgen_map = registry('svgen/map')
        self.wrapper = wrapper
        self.top = top
        self.outdir = outdir

    def Gear(self, node):
        svgen = self.svgen_map.get(node, None)
        if svgen is not None:
            svgen.generate(self.template_env, self.outdir)

            if (self.wrapper) and (node is self.top):
                yield f'wrap_{svgen.file_basename}', svgen.get_synth_wrap(
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
    if not conf['generate']:
        return top

    v = SVGenGenerateVisitor(top, conf['outdir'], conf.get('wrapper', False))
    for file_names, contents in v.visit(top):
        if contents:
            if isinstance(contents, (tuple, list)):
                for fn, c in zip(file_names, contents):
                    save_file(fn, conf['outdir'], c)
            else:
                save_file(file_names, conf['outdir'], contents)

    return top
