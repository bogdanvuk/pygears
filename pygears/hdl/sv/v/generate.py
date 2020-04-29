import os
from pygears.core.hier_node import HierYielderBase
from pygears.util.fileio import save_file
from pygears.hdl.templenv import TemplateEnv
from pygears import registry
from .util import vgen_intf, vgen_signal


class VTemplateEnv(TemplateEnv):
    lang = 'v'
    def __init__(self):
        super().__init__(basedir=os.path.dirname(__file__))

        self.jenv.globals.update(vgen_intf=vgen_intf,
                                 vgen_signal=vgen_signal)

        self.snippets = self.load(self.basedir, 'snippet.j2').module


class VGenGenerateVisitor(HierYielderBase):
    def __init__(self, top, outdir, wrapper=False):
        self.template_env = VTemplateEnv()
        self.vgen_map = registry('vgen/map')
        self.wrapper = wrapper
        self.top = top
        self.outdir = outdir

    def Gear(self, node):
        vgen = self.vgen_map.get(node, None)
        if vgen is not None:
            vgen.generate(self.template_env, self.outdir)

            # contents = vgen.get_module(self.template_env)
            # yield vgen.file_basename, contents

            # wrappers not needed for verilog, hence no else
            if (self.wrapper) and (node is self.top):
                yield f'wrap_{vgen.file_basename}', vgen.get_synth_wrap(
                    self.template_env)


def vgen_generate(top, conf):
    if not conf['generate']:
        return top

    v = VGenGenerateVisitor(top, conf['outdir'], conf.get('wrapper', False))
    for file_names, contents in v.visit(top):
        if contents:
            if isinstance(contents, (tuple, list)):
                for fn, c in zip(file_names, contents):
                    save_file(fn, conf['outdir'], c)
            else:
                save_file(file_names, conf['outdir'], contents)

    return top
