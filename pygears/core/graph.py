from pygears.conf import reg, PluginBase, Inject, inject
from pygears.core.port import InPort, OutPort, Port, HDLConsumer, HDLProducer
from pygears.core.hier_node import HierNode

sim_reg = None

class PathError(Exception):
    pass

def get_sim_map_gear(gear):
    global sim_reg
    if sim_reg is None:
        sim_reg = reg['sim']

    sim_map = sim_reg['map']
    while gear is not None:
        if gear in sim_map:
            return sim_map[gear]
        gear = gear.parent

    return None


def get_sim_cls_parent(gear_inst):
    parent = gear_inst.parent
    while parent is not None:
        if parent.params.get('sim_cls', None):
            break

        parent = parent.parent

    return parent


def is_end_consumer(obj, sim=False):
    if isinstance(obj, InPort):
        obj = obj.consumer

    if sim:
        if isinstance(obj.producer, InPort):
            if obj.producer.gear.params.get('sim_cls', None) is not None:
                return True

            if get_sim_cls_parent(obj.producer.gear):
                return False

    if (len(obj.consumers) == 1 and isinstance(obj.consumers[0], HDLConsumer)):
        return True

    return False


def is_source_producer(obj, sim=False):
    if not obj.consumers:
        return False

    if sim:
        # Check if intf drives output port of a sim_cls module
        for c in obj.consumers:
            if not isinstance(c, OutPort):
                continue

            if c.gear.params.get('sim_cls', None) is not None:
                return True

        for c in obj.consumers + [obj.producer]:
            if not isinstance(c, OutPort):
                continue

            if get_sim_cls_parent(c.gear):
                return False

    return isinstance(obj.producer, HDLProducer)


def get_source_producer(obj, sim=False):
    if isinstance(obj, Port):
        obj = obj.producer

    if is_source_producer(obj, sim=sim):
        return obj

    if isinstance(obj.producer, HDLProducer) or obj.producer is None:
        if sim:
            raise PathError(
                f'No producer found on beginning of the path: ?'
            )

        return obj

    err = None
    try:
        return get_source_producer(obj.producer, sim=sim)
    except PathError as e:
        err = e

    raise PathError(f'{str(err)} -> {obj.name}')


def _get_consumer_tree_rec(root_intf, cur_intf, consumers, end_producer):
    for port in cur_intf.consumers:
        if isinstance(port, HDLConsumer):
            continue

        cons_intf = port.consumer
        if is_end_consumer(cons_intf, sim=True):
            end_producer[port] = (root_intf, len(consumers))
            end_producer[cons_intf] = end_producer[port]
            consumers.append(port)
        else:
            start = len(consumers)
            _get_consumer_tree_rec(root_intf, cons_intf, consumers,
                                   end_producer)
            if len(consumers) - start > 1:
                end_producer[port] = (root_intf, slice(start, len(consumers)))
            else:
                end_producer[port] = (root_intf, start)

            end_producer[cons_intf] = end_producer[port]


def hier_dfs(root):
    yield root
    for c in root.child:
        yield from hier_dfs(c)


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
    consumer_tree = reg['graph/consumer_tree']
    end_producer = reg['graph/end_producer']
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
        reg['graph/consumer_tree'] = {}
        reg['graph/end_producer'] = {}


def get_producer_queue(obj):
    end_producer = reg['graph/end_producer']
    if obj not in end_producer:
        intf = get_source_producer(obj, sim=True)
        get_consumer_tree(intf)

    # TODO: investigate why this is necessary
    if obj not in end_producer:
        return None

    intf, i = end_producer[obj]
    if i >= len(intf.out_queues):
        # TODO: Investigate this. This happens when consumers tries to get
        # data, but somewhere along the path from the producer to the consumer,
        # some intermediate consumer is not registered with its immediate producer
        return None

    return intf.out_queues[i]
