from pygears.svgen.module_base import SVGenGearBase
from pygears.svgen.inst import SVGenInstPlugin


class SVGenHier(SVGenGearBase):
    def __init__(self, module, parent=None):
        super().__init__(module, parent)

    # def connect(self):
    #     self.arg_intf_map = {
    #         self.context.get_svgen(arg): name
    #         for arg, name in zip(self.module.args, self.module.argnames)
    #     }

    def get_module(self):

        context = {
            'module_name': self.sv_module_name,
            'generics': [],
            'intfs': list(self.sv_port_configs()),
            'inst': []
        }

        # for ointf, oname in zip(self.out_intfs, self.outname):
        #     ointf.rename = oname
        #     ointf.implicit = True

        for cgen in self.local_interfaces():
            contents = cgen.get_inst()
            if contents:
                context['inst'].append(contents)

        for cgen in self.local_modules():
            if hasattr(cgen, 'get_inst'):
                contents = cgen.get_inst()
                if contents:
                    context['inst'].append(contents)

        return self.context.jenv.get_template("hier_module.j2").render(context)


class SVGenHierPlugin(SVGenInstPlugin):
    @classmethod
    def bind(cls):
        cls.registry['SVGenModuleNamespace']['Hier'] = SVGenHier
