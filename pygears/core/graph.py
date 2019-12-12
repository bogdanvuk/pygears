from pygears.conf import registry, safe_bind, PluginBase, Inject, inject
from pygears.core.port import InPort, OutPort, Port
from pygears.core.hier_node import HierNode

sim_reg = None


def get_sim_map_gear(gear):
    global sim_reg
    if sim_reg is None:
        sim_reg = registry('sim')

    sim_map = sim_reg['map']
    while gear is not None:
        if gear in sim_map:
            return sim_map[gear]
        gear = gear.parent

    return None


def _get_consumer_tree_rec(root_intf, cur_intf, consumers, end_producer):
    for port in cur_intf.consumers:
        cons_intf = port.consumer
        sim_mod = get_sim_map_gear(port.gear)

        # If cur_intf -> port connection goes through the input port of a
        # Simulation module, we have found the end-point consumer
        if sim_mod and (isinstance(port, InPort)):
            # This might be a false-positive when this is a connection within
            # the simulation module
            if (cur_intf.producer
                    and cur_intf.producer.gear is not sim_mod.gear
                    and sim_mod.gear.has_descendent(cur_intf.producer.gear)):
                continue

            end_producer[port] = (root_intf, len(consumers))
            consumers.append(port)
        else:
            start = len(consumers)
            _get_consumer_tree_rec(root_intf, cons_intf, consumers,
                                   end_producer)
            if len(consumers) - start > 1:
                end_producer[port] = (root_intf, slice(start, len(consumers)))
            else:
                end_producer[port] = (root_intf, start)

        end_producer[port.consumer] = end_producer[port]


def hier_dfs(root):
    yield root
    for c in root.child:
        yield from hier_dfs(c)


def gear_from_rtl_port(rtl_port):
    node = rtl_port.node
    if not hasattr(node, 'gear'):
        return None

    if rtl_port.direction == "in":
        if rtl_port.index >= len(node.gear.in_ports):
            return None

        return node.gear.in_ports[rtl_port.index]
    else:
        if rtl_port.index >= len(node.gear.out_ports):
            return None

        return node.gear.out_ports[rtl_port.index]


@inject
def rtl_from_gear_port(gear_port, rtl_map=Inject('rtl/gear_node_map')):
    node = rtl_map.get(gear_port.gear, None)
    rtl_port = None
    if node:
        if isinstance(gear_port, InPort):
            port_group = node.in_ports
        else:
            port_group = node.out_ports

        rtl_port = port_group[gear_port.index]

    return rtl_port


def closest_gear_port_from_rtl(rtl_port, direction):
    gear_port = None

    while not gear_port and rtl_port:
        gear_port = gear_from_rtl_port(rtl_port)
        if not gear_port:
            if direction == 'in':
                if rtl_port.producer is None:
                    return None

                rtl_port = rtl_port.producer.producer
            else:
                if rtl_port.consumer is None:
                    return None

                rtl_port = rtl_port.consumer.consumers[0]

    return gear_port


def closest_rtl_from_gear_port(gear_port):
    rtl_port = None

    while not rtl_port and gear_port:
        rtl_port = rtl_from_gear_port(gear_port)
        if not rtl_port:
            if isinstance(gear_port, InPort):
                gear_port = gear_port.producer.producer
            else:
                gear_port = gear_port.consumer.consumers[0]

    return rtl_port


def _interface_tree_rec(node):
    for c in node.intf.consumers:
        child = HierNode(node)
        child.port = c
        child.intf = c.consumer
        _interface_tree_rec(child)


def interface_tree(intf):
    root_intf = intf

    while root_intf.producer is not None:
        root_intf = root_intf.producer.producer

    tree = HierNode()
    tree.intf = root_intf
    tree.port = root_intf.producer
    _interface_tree_rec(tree)

    for node in hier_dfs(tree):
        if node.intf is intf:
            return node


def get_consumer_tree(intf):
    consumer_tree = registry('graph/consumer_tree')
    end_producer = registry('graph/end_producer')
    if intf in consumer_tree:
        return consumer_tree[intf]

    consumers = []
    _get_consumer_tree_rec(intf, intf, consumers, end_producer)
    return consumers


class IntfOperPlugin(PluginBase):
    @classmethod
    def bind(cls):
        global sim_reg
        sim_reg = None
        safe_bind('graph/consumer_tree', {})
        safe_bind('graph/end_producer', {})


def get_end_producer(obj):
    if isinstance(obj, Port):
        return get_end_producer(obj.producer)
    else:
        for pout in obj.consumers:
            if pout.gear in registry('sim/map') and (isinstance(pout,
                                                                OutPort)):
                return obj
        else:
            if obj.producer:
                return get_end_producer(obj.producer)
            else:
                raise Exception(
                    f'Interface path does not end with a simulation gear at {pout.gear.name}.{pout.basename}'
                )


def get_producer_queue(obj):
    end_producer = registry('graph/end_producer')
    if obj not in end_producer:
        intf = get_end_producer(obj)
        get_consumer_tree(intf)

    # TODO: investigate why this is necessary
    if obj not in end_producer:
        return None

    intf, i = end_producer[obj]
    return intf.out_queues[i]
