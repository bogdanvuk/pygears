from collections import OrderedDict
from pygears.core.hier_node import NamedHierNode
from collections import Counter
from pygears.svgen.svstruct import SVStruct


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


def make_unique_name(objs, getter, setter):
    child_names = [getter(c) for c in objs]
    cnts = Counter(child_names)
    indexes = {k: 0 for k in cnts}
    for c in objs:
        name = getter(c)
        basename = name
        while cnts[name] > 1:
            indexes[basename] += 1
            name = f'{basename}{indexes[name]-1}'
            while name in indexes:
                indexes[basename] += 1
                name = f'{basename}{indexes[basename]-1}'

        setter(c, name)


class SVGenNodeBase(NamedHierNode):
    def __init__(self, parent, name, in_ports=[], out_ports=[]):
        super().__init__(name, parent)
        self.in_ports = in_ports.copy()
        self.out_ports = out_ports.copy()

    def bypass(self):
        if not (len(self.in_ports) == 1 and len(self.out_ports) == 1):
            raise Exception(
                'Can only bypass single input, single output modules')

        iin = self.in_ports[0].producer
        iout = self.out_ports[0].consumer
        self.remove()

        for port in iout.consumers:
            iout.disconnect(port)
            iin.connect(port)
            iout.remove()

    def remove(self):
        for p in self.in_ports:
            if p.producer is not None:
                p.producer.disconnect(p)

        for p in self.out_ports:
            p.consumer.producer = None

        # for p in self.out_ports:
        #     p['intf'].producer = None

        super().remove()

    def add_port(self, name, dir_, intf, type_, id_=None):
        if id_ is None:
            if dir_ == "in":
                id_ = len(list(self.in_ports()))
            else:
                id_ = len(list(self.out_ports()))

        self.ports.append({
            'name': name,
            'dir': dir_,
            'intf': None,
            'type': type_,
            'id': id_
        })
        if intf:
            self.connect_intf(self.ports[-1], intf)

        return self.ports[-1]

    @property
    def sv_module_name(self):
        trimmed_name = self.name
        if trimmed_name.startswith('/'):
            trimmed_name = trimmed_name[1:]

        return trimmed_name.replace('/', '_')

    @property
    def consumers(self):
        consumers = []
        for p in self.out_ports:
            iout = p.consumer
            consumers.extend(iout.consumers)

        return consumers

    def connect_intf(self, port, intf):
        if port['dir'] == 'in':
            if port['intf']:
                port['intf'].consumers.remove((self, port['id']))

            port['intf'] = intf
            intf.consumers.add((self, port['id']))
        else:
            if port['intf']:
                port['intf'].producer = None

            port['intf'] = intf
            intf.producer = (self, port['id'])

        port['type'] = intf.type

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

    def get_module(self, template_env):
        pass

    def get_fn(self):
        pass

    def get_synth_wrap(self):
        pass

    def get_params(self):
        return OrderedDict()

    def get_inst(self):
        pass


class SVGenDefaultNode(SVGenNodeBase):
    def sv_port_configs(self):
        for p in self.in_ports:
            yield self.get_sv_port_config(
                'consumer', type_=p.producer.dtype, name=p.basename)

        for p in self.out_ports:
            yield self.get_sv_port_config(
                'producer', type_=p.consumer.dtype, name=p.basename)

    def get_sv_port_config(self, modport, type_, name):
        return {
            'modport': modport,
            'name': name,
            'type': str(type_),
            'width': int(type_),
            'struct': SVStruct(name, type_)
        }

    def get_fn(self):
        return self.sv_module_name + ".sv"

    def get_synth_wrap(self):

        context = {
            'module_name': self.sv_module_name,
            'intfs': list(self.sv_port_configs()),
            'param_map': self.get_params()
        }
        return self.context.jenv.get_template("module_synth_wrap.j2").render(
            **context)

    def get_params(self):
        return OrderedDict()

    def get_out_port_map_intf_name(self, port):
        return port.consumer.basename

    def get_in_port_map_intf_name(self, port):
        intf = port.producer

        if len(intf.consumers) == 1:
            return intf.outname
        else:
            i = intf.consumers.index(port)
            return f'{intf.outname}[{i}]'

    def update_port_name(self, port, name):
        port['name'] = name

    def consolidate_names(self):
        make_unique_name(self.ports, lambda p: p['name'],
                         self.update_port_name)

    def get_inst(self, template_env):
        param_map = self.get_params()

        in_port_map = [(port.basename, self.get_in_port_map_intf_name(port))
                       for port in self.in_ports]

        out_port_map = [(port.basename, self.get_out_port_map_intf_name(port))
                        for port in self.out_ports]

        context = {
            'module_name': self.sv_module_name,
            'inst_name': self.basename + "_i",
            'param_map': param_map,
            'port_map': OrderedDict(in_port_map + out_port_map)
        }

        return template_env.snippets.module_inst(**context)
