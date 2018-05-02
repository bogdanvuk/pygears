from pygears.rtl.intf import RTLIntf
from pygears.rtl.node import RTLNode
from pygears.svgen.generate import svgen_generate
from pygears.svgen.inst import SVGenInstPlugin
from pygears.svgen.svgen import svgen_visitor
from pygears.core.hier_node import HierVisitorBase
from pygears.svgen.svmod import SVModuleGen
from pygears import registry


class SVGenHier(SVModuleGen):
    def local_interfaces(self):
        for child in self.node.child:
            if isinstance(child, RTLIntf):
                yield child

    def local_modules(self):
        for child in self.node.child:
            if isinstance(child, RTLNode):
                yield child

    def get_module(self, template_env):

        self.svgen_map = registry('SVGenMap')

        context = {
            'module_name': self.sv_module_name,
            'generics': [],
            'intfs': list(self.sv_port_configs()),
            'inst': []
        }

        for child in self.local_interfaces():
            svgen = self.svgen_map[child]
            contents = svgen.get_inst(template_env)
            if contents:
                context['inst'].append(contents)

        for child in self.local_modules():
            svgen = self.svgen_map[child]
            if hasattr(svgen, 'get_inst'):
                contents = svgen.get_inst(template_env)
                if contents:
                    context['inst'].append(contents)

        return template_env.render_local(__file__, "hier_module.j2", context)


@svgen_visitor
class RemoveEqualReprCastVisitor(HierVisitorBase):
    def SVGenHier(self, svmod):
        super().HierNode(svmod)

        if all([isinstance(c, RTLIntf) for c in svmod.child]):
            svmod.bypass()


class SVGenHierPlugin(SVGenInstPlugin):
    @classmethod
    def bind(cls):
        cls.registry['SVGenModuleNamespace']['Hier'] = SVGenHier
        cls.registry['SVGenFlow'].insert(
            cls.registry['SVGenFlow'].index(svgen_generate),
            RemoveEqualReprCastVisitor)
