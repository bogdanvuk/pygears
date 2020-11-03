import os
import re

from vcd.gtkw import GTKWSave

from pygears import find, reg
from pygears.core.port import OutPort as GearOutPort
from pygears.rtl.port import InPort, OutPort
from pygears.sim import log
from pygears.sim.extens.graphviz import graph
from pygears.sim.extens.vcd import module_sav
from pygears.sim.modules.sim_socket import SimSocket
from .activity import ActivityChecker


def _get_end_consumer_rec(intf, consumers):
    for port in intf.consumers:
        cons_intf = port.consumer

        if isinstance(port, InPort) and (not cons_intf.consumers):
            consumers.append(port)
        else:
            _get_end_consumer_rec(cons_intf, consumers)


def get_end_consumer(intf):
    consumers = []
    _get_end_consumer_rec(intf, consumers)
    return consumers


def _get_producer_rec(intf, producers):
    if isinstance(intf.producer, OutPort) or isinstance(
            intf.producer, GearOutPort):
        producers.append(intf.producer)
    else:
        _get_producer_rec(intf.producer, producers)


def get_producer(intf):
    producers = []
    _get_producer_rec(intf, producers)
    return producers


def find_target_prod(intf):
    # Who is producer gear?
    # prod_rtl_port = intf.producer
    end_p = get_producer(intf)
    if len(end_p) != 1:
        return None
    if isinstance(end_p[0], OutPort):
        prod_rtl_port = end_p[0]
        prod_rtl_node = prod_rtl_port.node
        prod_gear = prod_rtl_node.gear
    else:
        prod_gear = end_p[0].gear
    if len(prod_gear.child):
        if len(prod_gear.child) > 1:
            log.warning(
                f'ActivityCosim: prod has more than one child. Setting on first.'
            )
        return prod_gear.child[0]
    else:
        return prod_gear


def find_target_cons(intf):
    # Who is consumer port? Case when not broadcast!
    # cons_rtl_port = intf.consumers[0]
    end_c = get_end_consumer(intf)
    if len(end_c) != 1:
        if len(end_c) > 1:
            log.debug(f'Find target cons: found broadcast')
        return None
    cons_rtl_port = end_c[0]
    cons_rtl_node, port_id = cons_rtl_port.node, cons_rtl_port.index
    cons_gear = cons_rtl_node.gear
    cons_port = cons_gear.in_ports[port_id]

    return cons_port


def find_target_intf(gear_name, intf_name):
    gear_mod = find(gear_name)
    rtl_node = reg['rtl/gear_node_map'][gear_mod].node

    intf_name = intf_name[1:]  # spy name always starts with _
    for i in rtl_node.local_interfaces():
        if reg['hdlgen/map'][i].basename == intf_name:
            return i


def set_waiting_edge(g, port):
    g.edge_map[port].set_color('blue')
    g.edge_map[port].set_penwidth(6)


def set_blocking_edge(g, port):
    g.edge_map[port].set_color('red')
    g.edge_map[port].set_penwidth(6)


def set_blocking_node(g, module):
    g.node_map[module].set_fillcolor('red')
    g.node_map[module].set_style('filled')


class ActivityReporter(ActivityChecker):
    def __init__(self, top, draw_graph=True, cosim_check=False):
        super().__init__(top)
        self.draw_graph = draw_graph
        self.cosim_check = cosim_check

    def after_run(self, sim):
        if self.draw_graph:
            g = graph(
                outdir=reg['results-dir'],
                node_filter=lambda g: not g.child)
        else:
            g = None

        blocking_gears = set()
        cosim_name = None
        for sim_gear in sim.sim_gears:
            if isinstance(sim_gear, SimSocket):
                cosim_name = sim_gear.gear.name
                break
        if cosim_name and self.cosim_check:
            self.cosim_activity(g, cosim_name)
        self.sim_gears_activity(g, sim, blocking_gears)

        if self.draw_graph:
            outdir = reg['results-dir']
            g.graph.write_svg(os.path.join(outdir, 'proba.svg'))

        try:
            vcd_writer = reg['VCD']
        except KeyError:
            return

        with open(os.path.join(outdir, 'issue.gtkw'), 'w') as f:
            gtkw = GTKWSave(f)
            for module in blocking_gears:
                module_sav(gtkw, module, vcd_writer.vcd_vars)

    def sim_gears_activity(self, g, sim, blocking_gears):
        for sim_gear in sim.sim_gears:
            if isinstance(sim_gear, SimSocket):
                continue
            module = sim_gear.gear
            if self.draw_graph:
                g.node_map[module].set_style('filled')
                if sim_gear not in sim.done:
                    g.node_map[module].set_fillcolor('yellow')

        def data_in_decouple(module):
            if self.draw_graph:
                set_blocking_node(g, module)
            blocking_gears.add(module)

        def not_ack(module, p):
            if self.draw_graph:
                set_blocking_edge(g, p)
            blocking_gears.add(module)

        def waiting(module, p):
            if self.draw_graph:
                set_waiting_edge(g, p)

        self.hooks['data_in_decouple'] = data_in_decouple
        self.hooks['not_ack'] = not_ack
        self.hooks['waiting'] = waiting
        super().after_run(sim)

    def cosim_activity(self, g, top_name):
        outdir = reg['results-dir']
        activity_path = os.path.join(outdir, 'activity.log')

        if not os.path.isfile(activity_path):
            return

        with open(activity_path, 'r') as log:
            for line in log:
                activity_name = line.rpartition(': ')[0]
                activity_name = activity_name.replace('top.dut.',
                                                      f'{top_name}/')
                activity_name = activity_name.rpartition('.')[0]
                activity_name = activity_name.replace('_i.', '/')
                gear_name, _, intf_name = activity_name.rpartition('/')

                # Const always has valid high
                const_regex = r'.*_const(?P<num>\d+)_s'
                const_regex_one = r'.*_const_s'
                if not (re.match(const_regex, intf_name)
                        or re.match(const_regex_one, intf_name)):
                    log.error(
                        f'Cosim spy not acknowledged: {activity_name}')

                if self.draw_graph:
                    bc_regex = r'.*_bc_(?P<num>\d+).*'
                    if re.match(bc_regex, intf_name):
                        log.debug(
                            f'Activity monitor cosim: bc not supported {activity_name}'
                        )
                        continue

                    intf = find_target_intf(gear_name, intf_name)
                    if intf is None:
                        log.error(
                            f'Cannot find matching interface for {activity_name}'
                        )
                        continue
                    if intf.is_broadcast:
                        log.debug(
                            f'Intf bc not supported {activity_name}')
                        continue

                    try:
                        prod_gear = find_target_prod(intf)
                        set_blocking_node(g, prod_gear)
                    except (KeyError, AttributeError):
                        log.debug(
                            f'Cannot find node for {activity_name}')

                    try:
                        cons_port = find_target_cons(intf)
                        set_blocking_edge(g, cons_port)
                    except (KeyError, AttributeError):
                        log.debug(
                            f'Cannot find edge for {activity_name}')
