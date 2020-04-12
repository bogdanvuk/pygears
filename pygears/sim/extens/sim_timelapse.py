import os
from pygears import find
from pygears.sim.extens.sim_extend import SimExtend
from pygears.sim.extens import graphviz


class SimTimelapse(SimExtend):
    node_state_color_map = {
        'forward': 'green',
        'back': 'orange',
        'finished': 'red'
    }

    edge_state_color_map = {
        'new': 'black',
        'forward': 'green',
        'back': 'orange',
        'finished': 'red'
    }

    def __init__(self, outdir='timelapse', dpi=60):
        super().__init__()
        self.outdir = os.path.abspath(
            os.path.expandvars(os.path.expanduser(outdir)))
        os.makedirs(self.outdir, exist_ok=True)
        self.g = graphviz.graph(find('/'), edge_fmt='{prod_gear} -> {cons_gear}')
        self.g.set_dpi(dpi)
        self.img_cnt = 0

        for out_port in self.g.prod_edge_map:
            out_port.producer.events['put'].append(self.intf_put)

        for in_port in self.g.cons_edge_map:
            in_port.consumer.events['ack'].append(self.intf_ack)
            in_port.consumer.events['finish'].append(self.intf_finish)

    @property
    def cur_img_file_name(self):
        return os.path.join(self.outdir, f'img_{self.img_cnt:04}.gif')

    def mark_done(self, sim):
        for sim_module in sim.sim_gears:
            if sim_module.done:
                self.g.node_map[sim_module.gear].set_style('filled')
                self.g.node_map[sim_module.gear].set_fillcolor('red')

    def color_node(self, node, state=None):
        if state:
            node.set_style('filled')
            node.set_fillcolor(self.node_state_color_map[state])
        elif self.get_node_state(node) != 'finished':
            node.set_style('')

    def get_node_state(self, node):
        return list(self.node_state_color_map.keys())[list(
            self.node_state_color_map.values()).index(node.get_fillcolor())]

    def color_edge(self, edge, state=None):
        if state:
            edge.set_color(self.node_state_color_map[state])
            edge.set_penwidth(6)
        else:
            if self.get_edge_state(edge) != 'finished':
                edge.set_color('black')
                edge.set_penwidth(1)

            edge.set_taillabel('')

    def get_edge_state(self, edge):
        return list(self.edge_state_color_map.keys())[list(
            self.edge_state_color_map.values()).index(edge.get_color())]

    def intf_finish(self, intf):
        if intf.producer:
            self.color_edge(self.g.cons_edge_map[intf.producer], 'finished')

    def intf_put(self, intf, val):
        for port in intf.end_consumers:
            edge = self.g.cons_edge_map[port]
            self.color_edge(edge, 'forward')
            edge.set_taillabel(f'< <B>{str(val)}</B> >')

    def intf_ack(self, intf):
        self.color_edge(self.g.cons_edge_map[intf.producer], 'back')

    def after_call_forward(self, sim, sim_gear):
        module = sim_gear.gear
        self.color_node(self.g.node_map[module], 'forward')

        self.mark_done(sim)

        self.snapshot()

        self.color_node(self.g.node_map[module], None)

        return True

    def after_call_back(self, sim, sim_gear):
        module = sim_gear.gear
        self.color_node(self.g.node_map[module], 'back')

        self.mark_done(sim)

        for port in module.out_ports:
            edges = self.g.prod_edge_map[port]
            for e in edges:
                self.color_edge(e, None)

        self.snapshot()

        self.color_node(self.g.node_map[module], None)

        return True

    def snapshot(self):
        self.g.write_gif(self.cur_img_file_name)
        self.img_cnt += 1

    def after_cleanup(self, sim):
        self.mark_done(sim)
        self.snapshot()
