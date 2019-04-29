from pygears.conf import registry, safe_bind, PluginBase, Inject, inject
from pygears.core.port import InPort, OutPort, Port


def _get_consumer_tree_rec(root_intf, cur_intf, consumers, end_producer):

    for port in cur_intf.consumers:
        cons_intf = port.consumer
        if (port.gear in registry('sim/map')) and (isinstance(port, InPort)):
            # if not cons_intf.consumers:
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


from pygears.core.hier_node import HierNode


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

    intf, i = end_producer[obj]
    return intf.out_queues[i]
