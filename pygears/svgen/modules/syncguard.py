from pygears.core.hier_node import HierNode


class SVGenSyncGuard(HierNode):
    def __init__(self, name, size, context, parent):
        super().__init__(parent)
        self.name = name
        self.context = context
        self.size = size
        self.intf_ports = []

        for i in range(size):
            self.add_port('consumer', f'din{i}')
            self.add_port('producer', f'dout{i}')

    def get_fn(self):
        return self.name + ".sv"

    def add_port(self, modport, name):
        self.intf_ports.append({'modport': modport, 'name': name})

    def get_module(self, template_env):
        context = {'module_name': self.name, 'intfs': self.intf_ports}
        return template_env.render_local(__file__, "syncguard.j2", context)
