import os

from vcd.gtkw import GTKWSave

from pygears import find, registry
from pygears.common.decoupler import decoupler_din
from pygears.sim import sim_log
from pygears.sim.extens.graphviz import graph
from pygears.sim.extens.vcd import module_sav


def find_target_prod_cons(gear_name, intf_name):
    gear_mod = find(gear_name)
    rtl_node = registry('RTLNodeMap')[gear_mod].node

    intf = find_target_intf(intf_name, rtl_node)

    # Who is producer gear?
    prod_rtl_port = intf.producer
    prod_rtl_node = prod_rtl_port.node
    prod_gear = prod_rtl_node.gear

    # Who is consumer port? Case when not broadcast!
    cons_rtl_port = intf.consumers[0]
    cons_rtl_node, port_id = cons_rtl_port.node, cons_rtl_port.index
    cons_gear = cons_rtl_node.gear
    cons_port = cons_gear.in_ports[port_id]

    return prod_gear, cons_port


def find_target_intf(intf_name, rtl_node):
    intf_name = intf_name[1:]
    for i in rtl_node.local_interfaces():
        if registry('SVGenMap')[i].basename == intf_name:
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


class ActivityReporter:
    def __init__(self, top):
        sim = registry('Simulator')
        sim.events['before_run'].append(self.before_run)
        sim.events['after_run'].append(self.after_run)
        self.blockers = {}

    def intf_pull_start(self, intf):
        consumer = intf.producer
        producer = intf.in_queue.intf.consumers[0]
        self.blockers[consumer] = producer
        return True

    def intf_pull_done(self, intf):
        consumer = intf.producer
        del self.blockers[consumer]
        return True

    def before_run(self, sim):
        sim_map = registry('SimMap')

        for module, sim_gear in sim_map.items():
            for p in module.in_ports:
                p.consumer.events['pull_start'].append(self.intf_pull_start)
                p.consumer.events['pull_done'].append(self.intf_pull_done)

    def after_run(self, sim):

        g = graph(
            outdir=registry('SimArtifactDir'),
            node_filter=lambda g: not g.child)

        blocking_gears = set()
        self.cosim_activity(g)
        self.sim_gears_activity(g, sim, blocking_gears)

        outdir = registry('SimArtifactDir')
        g.graph.write_svg(os.path.join(outdir, 'proba.svg'))

        try:
            vcd_writer = registry('VCD')
        except KeyError:
            return

        with open(os.path.join(outdir, 'issue.sav'), 'w') as f:
            gtkw = GTKWSave(f)
            for module in blocking_gears:
                module_sav(gtkw, module, vcd_writer.vcd_vars)

    def sim_gears_activity(self, g, sim, blocking_gears):
        for sim_gear in sim.sim_gears:
            from pygears.sim.modules.sim_socket import SimSocket
            if isinstance(sim_gear, SimSocket):
                continue

            module = sim_gear.gear

            g.node_map[module].set_style('filled')
            if sim_gear not in sim.done:
                g.node_map[module].set_fillcolor('yellow')

            if module.definition == decoupler_din:
                if not module.queue.empty():
                    set_blocking_node(g, module)
                    blocking_gears.add(module)
                    sim_log().error(f'Data left in decoupler: {module.name}')

            for p in module.in_ports:
                q = p.get_queue()
                # print(f'{module.name}.{p.basename} queue empty: {q.empty()}')
                if q._unfinished_tasks:
                    src_port = q.intf.consumers[0]
                    set_blocking_edge(g, p)
                    blocking_gears.add(module)
                    sim_log().error(
                        f'{src_port.gear.name}.{src_port.basename} -> {module.name}.{p.basename} was not acknowledged'
                    )

                if p in self.blockers:
                    set_waiting_edge(g, p)
                    src_port = self.blockers[p]
                    sim_log().info(
                        f'{p.gear.name}.{p.basename} waiting on {src_port.gear.name}.{src_port.basename}'
                    )

    def cosim_activity(self, g):
        outdir = registry('SimArtifactDir')
        activity_path = os.path.join(outdir, 'activity.log')

        if not os.path.isfile(activity_path):
            return

        with open(activity_path, 'r') as log:
            for line in log:
                activity_name = line.rpartition(': ')[0]
                # TODO: hardcoded!!!
                activity_name = activity_name.replace('top.dut.', '/ostream/')
                activity_name = activity_name.rpartition('.')[0]
                activity_name = activity_name.replace('_i.', '/')
                gear_name, _, intf_name = activity_name.rpartition('/')

                try:
                    prod_gear, cons_port = find_target_prod_cons(
                        gear_name, intf_name)
                    set_blocking_node(g, prod_gear)
                    set_blocking_edge(g, cons_port)
                except (KeyError, AttributeError):
                    print(f'KeyError or AttributeError in cosim_activity')

                sim_log().error(
                    f'Cosim spy not acknowledged: {gear_name}.{intf_name}')
