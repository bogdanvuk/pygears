import os

from pygears.conf import registry
from pygears.svgen.generate import SVGenGenerateVisitor, TemplateEnv
from pygears.svgen.svmod import SVModuleGen
from pygears.util.fileio import save_file

from .util import vgen_intf, vgen_reg, vgen_wire
from .vcompile import compile_gear


class VModuleGen(SVModuleGen):
    @property
    def sv_file_name(self):
        svgen_params = self.node.params.get('svgen', {})
        return svgen_params.get('svmod_fn', self.sv_module_name + ".v")

    def get_module(self, template_env):
        if not self.is_generated:
            return None

        context = self.get_module_context()

        assert not self.is_hierarchical
        assert self.is_compiled

        return compile_gear(self.node.gear, template_env, context)


class VTemplateEnv(TemplateEnv):
    def __init__(self):
        super(VTemplateEnv, self).__init__()

        self.jenv.globals.update(
            vgen_intf=vgen_intf, vgen_wire=vgen_wire, vgen_reg=vgen_reg)

        self.basedir = os.path.dirname(__file__)
        self.snippets = self.load(self.basedir, 'snippet.j2').module


class VGenGenerateVisitor(SVGenGenerateVisitor):
    def __init__(self, top, wrapper=False):
        super(VGenGenerateVisitor, self).__init__(top, wrapper)
        self.template_env = VTemplateEnv()

    def RTLNode(self, node):
        svgen = self.svgen_map.get(node, None)
        if svgen is not None:
            if svgen.is_compiled:
                svgen = VModuleGen(node)  # replace default SVModuleGen
                contents = svgen.get_module(self.template_env)
                yield svgen.sv_file_name, contents
            # wrappers not needed for verilog, hence no else


def vgen_generate(top, conf):
    v = VGenGenerateVisitor(top, conf.get('wrapper', False))
    for file_names, contents in v.visit(top):
        if contents:
            if isinstance(contents, (tuple, list)):
                for fn, c in zip(file_names, contents):
                    save_file(fn, conf['outdir'], c)
            else:
                save_file(file_names, conf['outdir'], contents)

    return top
