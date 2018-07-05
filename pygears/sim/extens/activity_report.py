from pygears import registry
from pygears.common.decoupler import decoupler_din
from pygears.sim.extens.graphviz import graph
from pygears.sim.extens.vcd import module_sav
from vcd.gtkw import GTKWSave
from pygears.core.port import OutPort
import itertools
import os


class ActivityReporter:
    def __init__(self, top, conf):
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
        g = graph()

        blocking_gears = set()

        for sim_gear in sim.sim_gears:
            module = sim_gear.gear

            g.node_map[module].set_style('filled')
            if sim_gear not in sim.done:
                g.node_map[module].set_fillcolor('red')

            if module.definition == decoupler_din:
                if not module.queue.empty():
                    g.node_map[module].set_fillcolor('red')
                    g.node_map[module].set_style('filled')
                    blocking_gears.add(module)
                    print(f'Data left in decoupler: {module.name}')

            for p in module.in_ports:
                q = p.get_queue()
                # print(f'{module.name}.{p.basename} queue empty: {q.empty()}')
                if q._unfinished_tasks:
                    src_port = q.intf.consumers[0]
                    g.edge_map[p].set_color('red')
                    g.edge_map[p].set_penwidth(6)
                    blocking_gears.add(module)
                    print(
                        f'{src_port.gear.name}.{src_port.basename} -> {module.name}.{p.basename} was not acknowledged'
                    )

                if p in self.blockers:
                    g.edge_map[p].set_color('blue')
                    g.edge_map[p].set_penwidth(6)
                    src_port = self.blockers[p]
                    print(
                        f'{p.gear.name}.{p.basename} waiting on {src_port.gear.name}.{src_port.basename}'
                    )

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
