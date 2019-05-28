class SVGenSyncGuard:
    def __init__(self, name, size):
        self.size = size
        self.intf_ports = []
        self.basename = name

        for i in range(size):
            self.add_port('consumer', f'din{i}')
            self.add_port('producer', f'dout{i}')

    @property
    def file_name(self):
        return self.basename + ".sv"

    def add_port(self, modport, name):
        self.intf_ports.append({
            'modport': modport,
            'name': name,
            'type': None,
            'width': None
        })

    def get_module(self, template_env):
        context = {'module_name': self.basename, 'intfs': self.intf_ports}
        return template_env.render_local(__file__, "syncguard.j2", context)
