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


def is_end_consumer(port: Port, sim=False):
    if sim:
        if isinstance(port, InPort):
            if port.gear.params.get('sim_cls', None) is not None:
                return True

            if get_sim_cls_parent(port.gear):
                return False

    intf = port.consumer

    if intf is None:
        return True

    if (len(intf.consumers) == 1 and isinstance(intf.consumers[0], HDLConsumer)):
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
            raise PathError(f'No producer found on beginning of the path: ?')

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
        if is_end_consumer(port, sim=True):
            end_producer[port] = (root_intf, len(consumers))
            consumers.append(port)
        elif cons_intf is not None:
            start = len(consumers)
            _get_consumer_tree_rec(root_intf, cons_intf, consumers, end_producer)
            if len(consumers) - start > 1:
                end_producer[port] = (root_intf, slice(start, len(consumers)))
            else:
                end_producer[port] = (root_intf, start)


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


def get_end_producer(obj):
    end_producer = reg['graph/end_producer']
    if obj not in end_producer:
        intf = get_source_producer(obj, sim=True)
        get_consumer_tree(intf)

    # TODO: investigate why this is necessary
    if obj not in end_producer:
        return None

    return end_producer[obj]


def get_producer_queue(obj):
    intf, i = get_end_producer(obj.producer)
    if i >= len(intf.out_queues):
        # TODO: Investigate this. This happens when consumers tries to get
        # data, but somewhere along the path from the producer to the consumer,
        # some intermediate consumer is not registered with its immediate producer
        return None

    return intf.out_queues[i]


def get_producer_port(obj):
    if isinstance(obj, Port):
        obj = obj.producer

    return obj.producer


def has_async_producer(obj):
    port = get_producer_port(obj)
    return isinstance(port, HDLProducer)
