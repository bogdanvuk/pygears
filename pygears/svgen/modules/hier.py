from pygears.svgen.module_base import SVGenGearBase, SVGenIntfBase
from pygears.svgen.node_base import SVGenNodeBase
from pygears.svgen.inst import SVGenInstPlugin


class SVGenHier(SVGenGearBase):
    def __init__(self, module, parent=None):
        super().__init__(module, parent)

    # def connect(self):
    #     self.arg_intf_map = {
    #         self.context.get_svgen(arg): name
    #         for arg, name in zip(self.module.args, self.module.argnames)
    #     }

    def local_interfaces(self):
        for cgen in self.child:
            if isinstance(cgen, SVGenIntfBase):
                yield cgen

    def local_modules(self):
        for cgen in self.child:
            if isinstance(cgen, SVGenNodeBase):
                yield cgen

    def get_module(self, template_env):

        context = {
            'module_name': self.sv_module_name,
            'generics': [],
            'intfs': list(self.sv_port_configs()),
            'inst': []
        }

        for cgen in self.local_interfaces():
            contents = cgen.get_inst(template_env)
            if contents:
                context['inst'].append(contents)

        for cgen in self.local_modules():
            if hasattr(cgen, 'get_inst'):
                contents = cgen.get_inst(template_env)
                if contents:
                    context['inst'].append(contents)

        return template_env.render_local(__file__, "hier_module.j2", context)


class SVGenHierPlugin(SVGenInstPlugin):
    @classmethod
    def bind(cls):
        cls.registry['SVGenModuleNamespace']['Hier'] = SVGenHier