from pygears.core.hier_node import NamedHierNode, find_unique_names
from pygears.rtl.port import InPort, OutPort
from pygears.rtl.intf import RTLIntf


def is_in_subbranch(root, node):
    root_path = root.name.split('/')
    node_path = node.name.split('/')

    if len(root_path) > len(node_path):
        return False

    for r, n in zip(root_path, node_path):
        if r != n:
            return False
    else:
        return True


class RTLNode(NamedHierNode):
    def __init__(self, parent, name, params={}):
        super().__init__(name, parent)
        self.in_ports = []
        self.out_ports = []
        self.params = params.copy()

    def add_in_port(self, basename, producer=None, consumer=None, dtype=None):
        self.in_ports.append(
            InPort(
                node=self,
                index=len(self.in_ports),
                basename=basename,
                producer=producer,
                consumer=consumer,
                dtype=dtype))

        port_names = [p.basename for p in self.in_ports]
        for port, new_name in zip(self.in_ports, find_unique_names(port_names)):
            if new_name:
                port.basename = new_name

    def add_out_port(self, basename, producer=None, consumer=None, dtype=None):
        self.out_ports.append(
            OutPort(
                node=self,
                index=len(self.out_ports),
                basename=basename,
                producer=producer,
                consumer=consumer,
                dtype=dtype))

        port_names = [p.basename for p in self.out_ports]
        for port, new_name in zip(self.out_ports, find_unique_names(port_names)):
            if new_name:
                port.basename = new_name

    def bypass(self):
        if not (len(self.in_ports) == 1 and len(self.out_ports) == 1):
            raise Exception(
                'Can only bypass single input, single output modules')

        iin = self.in_ports[0].producer
        iout = self.out_ports[0].consumer
        self.remove()

        for port in iout.consumers.copy():
            iout.disconnect(port)
            iin.connect(port)

        iout.remove()

    def remove(self):
        for p in self.in_ports:
            if p.producer is not None:
                p.producer.disconnect(p)

        for p in self.out_ports:
            p.consumer.producer = None

        super().remove()

    @property
    def is_hierarchical(self):
        return any([isinstance(c, RTLNode) for c in self.child])

    def local_interfaces(self):
        for child in self.child:
            if isinstance(child, RTLIntf):
                yield child

    def local_modules(self):
        for child in self.child:
            if isinstance(child, RTLNode):
                yield child

    @property
    def consumers(self):
        consumers = []
        for p in self.out_ports:
            iout = p.consumer
            consumers.extend(iout.consumers)

        return consumers

    def channel_ports(self):
        # If this is a top level module, no ports need to be output further
        if self.parent is None:
            return

        for p in self.in_ports():
            if p['intf'].parent != self.parent and (
                    not self.parent.is_descendent(p['intf'].parent)):
                self.parent.in_port_make(p, self)

        for p in self.out_ports():
            consumers_at_same_level_or_sublevel = [
                is_in_subbranch(p['intf'].parent, c[0])
                for c in p['intf'].consumers
            ]
            if not all(consumers_at_same_level_or_sublevel) or (
                    not p['intf'].consumers):
                self.parent.out_port_make(p, self)
