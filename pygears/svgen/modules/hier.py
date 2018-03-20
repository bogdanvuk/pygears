from pygears.svgen.intf_base import SVGenIntfBase
from pygears.svgen.node_base import SVGenNodeBase, SVGenDefaultNode, make_unique_name
from pygears.svgen.module_base import SVGenModuleBase
from pygears.svgen.inst import SVGenInstPlugin


class SVGenPortModule(SVGenModuleBase):
    def channel_ports(self):
        iin = self.ports[0]['intf']
        iout = self.ports[1]['intf']
        iout.implicit = True

        self.remove()

        hier_port = self.parent.add_port(self.basename, 'in', iin,
                                         self.ports[0]['type'])
        self.parent.add_port_node(hier_port, SVGenPortSource, iout)
        # if iin.producer is None:
        #     hier_port = self.parent.add_port(self.basename, 'in', iin,
        #                                      self.ports[0]['type'])
        #     self.parent.add_port_node(hier_port, SVGenPortSource, iout)
        #     # self.parent = None
        #     # iin.parent = None
        #     # iout.parent = None

        #     # self.parent.in_port_make(self.ports[0], self)
        # else:
        #     for m in iout.consumers.copy():
        #         for p in m.get_intf_ports(iout):
        #             m.connect_intf(p, iin)


class SVGenPortSource(SVGenNodeBase):
    def __init__(self, port, parent):
        out_port = {
            'name': port['name'],
            'dir': 'out',
            'intf': None,
            'type': None,
            'id': 0
        }
        self.hier_port = port

        super().__init__(parent, port['name'], [out_port])

    def consolidate_names(self):
        self.ports[0]['name'] = self.hier_port['name']
        self.ports[0]['intf'].basename = self.hier_port['name']


class SVGenPortSink(SVGenNodeBase):
    def __init__(self, port, parent):
        in_port = {
            'name': port['name'],
            'dir': 'in',
            'intf': None,
            'type': None,
            'id': 0
        }
        self.hier_port = port

        super().__init__(parent, port['name'], [in_port])

    def consolidate_names(self):
        self.ports[0]['name'] = self.hier_port['name']
        self.ports[0]['intf'].basename = self.hier_port['name']


class SVGenHier(SVGenDefaultNode):
    def __init__(self, module, parent=None):
        self.module = module
        self.port_nodes = []
        super().__init__(parent, module.basename)

    def add_port_node(self, port, type_, intf):
        if type_ is SVGenPortSource:
            port_node = SVGenPortSource(port, self.context, parent=self)
        else:
            port_node = SVGenPortSink(port, self.context, parent=self)

        port_node.connect_intf(port_node.ports[0], intf)
        self.port_nodes.append(port_node)

    def update_port_name(self, port, name):
        port['name'] = name

    def in_port_make(self, port, node):
        intf = port['intf']

        # already_out = None
        # for p in self.port_nodes:
        #     if intf in list(get_intf_array(p.ports[0]['intf'])):
        #         already_out = p
        #         break

        # if already_out is not None:
        #     node.connect_intf(port, already_out.ports[1]['intf'])
        # else:
        port_name = self.arg_intf_map.get(intf, port['name'])

        local_cons = [c for c in intf.consumers if self.is_descendent(c[0])]

        local_intf = SVGenIntfBase(
            parent=self,
            name=port_name,
            type_=port['type'],
            producer=None,
            implicit=True)

        for m in local_cons:
            in_port = list(m[0].in_ports())[m[1]]
            m[0].connect_intf(in_port, local_intf)
            # for ip in m.get_intf_ports(intf):
            #     m.connect_intf(ip, local_intf)

        hier_port = self.add_port(port_name, 'in', intf, port['type'])
        self.add_port_node(hier_port, SVGenPortSource, local_intf)

    def out_port_make(self, port, node):
        intf = port['intf']

        # The interface intf is led out of the hierarchy block. Thus, it is
        # broken into two parts: intf which stays in this level of the
        # hierarchy and end at the port, and extern_intf which belongs to the
        # level of the hierarchy above
        extern_intf = SVGenIntfBase(
            parent=self.parent, name='', type_=port['type'])

        # Source extern_intf from the hierarchy port from the outside
        hier_port = self.add_port(port['name'], 'out', extern_intf,
                                  port['type'])

        # Sink intf into the port node from the inside
        self.add_port_node(hier_port, SVGenPortSink, intf)
        intf.implicit = True
        intf.basename = port['name']

        # Source the external consumers of the intf with extern_intf instead
        extern_cons = [c for c in intf.consumers if c[0].parent != self]
        for m in extern_cons:
            in_port = list(m[0].in_ports())[m[1]]
            m[0].connect_intf(in_port, extern_intf)
            # for p in m.get_intf_ports(intf):
            #     m.connect_intf(p, extern_intf)

    def connect(self):
        self.arg_intf_map = {
            self.context.get_svgen(arg): name
            for arg, name in zip(self.module.args, self.module.argnames)
        }

    def post_consolidate_names(self):
        make_unique_name(
            [c for c in self.child if isinstance(c, SVGenNodeBase)],
            lambda m: m.basename, lambda m, val: setattr(m, 'basename', val))

    def local_interfaces(self):
        for cgen in self.child:
            if isinstance(cgen, SVGenIntfBase):
                yield cgen

    def local_modules(self):
        for cgen in self.child:
            if isinstance(cgen, SVGenNodeBase):
                yield cgen

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
