from .intf import Intf
from pygears.conf import core_log
from pygears.core.graph import get_source_producer, get_producer_port
from pygears.core.hier_node import find_unique_names
from .port import InPort, OutPort
from .gear import OutSig, InSig


def connect_to_existing_parent_in_port(in_port):
    parent = in_port.gear.parent
    in_intf = in_port.producer
    src_intf = get_source_producer(in_port)

    for parent_port in parent.in_ports:
        if src_intf is get_source_producer(parent_port):
            in_intf.disconnect(in_port)
            parent_port.consumer.connect(in_port)
            return True

    return False


def connect_to_existing_parent_out_port(out_port, cons_port):
    parent = out_port.gear.parent
    out_intf = out_port.consumer

    for parent_port in parent.out_ports:
        if out_intf is parent_port.consumer:
            out_intf.disconnect(cons_port)
            parent_port.consumer.connect(cons_port)
            return True

    return False


# TODO: Dangling reporting not working anymore
def report_out_dangling(port):
    src_intf = get_source_producer(port)
    p = src_intf.consumers[0]

    if hasattr(src_intf, 'var_name'):
        core_log().warning(f'Interface "{p.gear.name}/{src_intf.var_name}" left dangling.')
    else:
        path = []
        while True:
            g = p.gear

            if hasattr(p.consumer, 'var_name'):
                path.append(f'{g.parent.name}/{p.consumer.var_name}')
            else:
                path.append(p.name)

            if len(g.in_ports) != 1 or len(g.out_ports) != 1:
                break

            p = get_producer_port(g.in_ports[0])

        path = ' -> '.join(reversed(path))

        core_log().warning(f'Interface "{path}" left dangling.')


def channel_out_port(gear_inst, out_port):
    out_parent_cons = []

    out_intf = out_port.consumer
    for cons_port in out_intf.consumers:
        cons_gear = cons_port.gear

        if gear_inst.parent.has_descendent(cons_gear):
            continue

        if connect_to_existing_parent_out_port(out_port, cons_port):
            continue

        out_parent_cons.append(cons_port)

    if out_intf.consumers and not out_parent_cons:
        return

    basename = getattr(out_intf, 'var_name', out_port.basename)
    new_name = next(
        find_unique_names(
            [basename] +
            [p.basename for p in (gear_inst.parent.out_ports + gear_inst.parent.in_ports)]))

    if new_name:
        basename = new_name

    parent_port = OutPort(gear_inst.parent, len(gear_inst.parent.out_ports), basename)

    gear_inst.parent.out_ports.append(parent_port)

    in_intf = Intf(out_intf.dtype)
    out_intf.source(parent_port)
    in_intf.source(out_port)
    in_intf.connect(parent_port)

    for p in out_intf.consumers:
        if p in out_parent_cons:
            continue

        out_intf.disconnect(p)
        in_intf.connect(p)


def channel_in_port(gear_inst, in_port):
    in_intf = in_port.producer
    prod_port = in_intf.producer

    if prod_port:
        if gear_inst.parent.has_descendent(prod_port.gear):
            return

    if connect_to_existing_parent_in_port(in_port):
        return

    basename = getattr(in_intf, 'var_name', in_port.basename)
    new_name = next(
        find_unique_names(
            [basename] +
            [p.basename for p in (gear_inst.parent.out_ports + gear_inst.parent.in_ports)]))

    if new_name:
        basename = new_name

    parent_port = InPort(gear_inst.parent, len(gear_inst.parent.in_ports), basename)

    gear_inst.parent.in_ports.append(parent_port)

    in_intf.disconnect(in_port)
    in_intf.connect(parent_port)

    gear_in_intf = Intf(in_intf.dtype)
    gear_in_intf.source(parent_port)
    gear_in_intf.connect(in_port)


def is_driven_by_node(node, name):
    for s in node.meta_kwds['signals']:
        if isinstance(s, OutSig):
            if s.name in node.params['sigmap']:
                if name == node.params['sigmap'][s.name]:
                    return s
            else:
                if name == s.name:
                    return s
    else:
        return None


def find_signal_driver_port(parent, name):
    for node in parent.child:
        if is_driven_by_node(node, name):
            return True

    for s in parent.meta_kwds['signals']:
        if isinstance(s, InSig):
            if s.name == name:
                return True

    return False


def channel_interfaces(gear_inst):
    for in_port in gear_inst.in_ports:
        channel_in_port(gear_inst, in_port)

    for out_port in gear_inst.out_ports:
        channel_out_port(gear_inst, out_port)

    for s in gear_inst.meta_kwds['signals']:
        if s.name not in gear_inst.params['sigmap']:
            gear_inst.params['sigmap'] = gear_inst.params['sigmap'].copy()
            gear_inst.params['sigmap'][s.name] = s.name

    for s in gear_inst.meta_kwds['signals']:
        if isinstance(s, InSig):
            sig_name = gear_inst.params['sigmap'].get(s.name, s.name)

            if not sig_name.isidentifier():
                continue

            # sig_name = s.name

            if not find_signal_driver_port(gear_inst.parent, sig_name):
                if not isinstance(gear_inst.parent.meta_kwds['signals'], list):
                    gear_inst.parent.meta_kwds['signals'] = list(
                        gear_inst.parent.meta_kwds['signals'])

                gear_inst.parent.meta_kwds['signals'] = gear_inst.parent.meta_kwds['signals'].copy()
                gear_inst.parent.meta_kwds['signals'].append(s)
