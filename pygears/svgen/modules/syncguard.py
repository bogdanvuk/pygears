from pygears.svgen.node_base import SVGenNodeBase


class SVGenSyncGuard(SVGenNodeBase):
    def __init__(self, parent, name, size):
        super().__init__(parent, name)
        self.size = size
        self.intf_ports = []

        for i in range(size):
            self.add_port('consumer', f'din{i}')
            self.add_port('producer', f'dout{i}')

    def get_fn(self):
        return self.basename + ".sv"

    def add_port(self, modport, name):
        self.intf_ports.append({'modport': modport, 'name': name})

    def get_module(self, template_env):
        context = {'module_name': self.basename, 'intfs': self.intf_ports}
        return template_env.render_local(__file__, "syncguard.j2", context)
