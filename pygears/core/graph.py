from pygears.conf import registry, safe_bind, PluginBase, Inject, reg_inject
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
