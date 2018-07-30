import pydot
import os
from pygears.core.port import InPort
from pygears.core.hier_node import HierVisitorBase
from pygears.util.find import find
from pygears import registry
from pygears.util import print_hier


class Visitor(HierVisitorBase):
    def __init__(self, node_filter, outdir):
        self.gear_map = {}
        self.node_map = {}
        self.graph = pydot.Dot(
            graph_type='digraph', rankdir='LR', overlap=False)
        self.hier = [self.graph]
        self.node_filter = node_filter
        self.outdir = outdir
        os.makedirs(self.outdir, exist_ok=True)

    def enter_hier(self, module):
        self.hier.append(self.gear_map[module])

    def exit_hier(self, module):
        node = self.hier.pop()
        self.hier[-1].add_subgraph(node)

    def Gear(self, module):
        gear_fn = module.name.replace('/', '_')
        if self.outdir:
            gear_stem = os.path.abspath(os.path.join(self.outdir, gear_fn))

            v = print_hier.Visitor(params=True, fullname=True)
            v.visit(module)
            with open(f'{gear_stem}.txt', 'w') as f:
                f.write('\n'.join(v.res))

        if self.node_filter(module):
            self.gear_map[module] = pydot.Node(
                module.name,
                tooltip=module.name,
                label=module.basename,
                URL=f"localhost:5000/{gear_fn}")

            self.node_map[module] = self.gear_map[module]
            self.hier[-1].add_node(self.gear_map[module])
        else:
            self.gear_map[module] = pydot.Cluster(
                graph_name=module.name,
                label=module.basename,
                tooltip=module.name,
                fontsize=48,
                fontcolor='blue',
                labeljust='l',
                overlap=False,
                # URL=f"file://{desc_fn}")
                URL=f"localhost:5000/{gear_fn}")

            self.enter_hier(module)

            super().HierNode(module)

            self.exit_hier(module)

        return True


def _get_consumer_tree_rec(intf, consumers, node_filter):
    for port in intf.consumers:
        cons_intf = port.consumer
        if node_filter(port.gear) and (isinstance(port, InPort)):
            consumers.append(port)
        else:
            _get_consumer_tree_rec(cons_intf, consumers, node_filter)


def get_consumer_tree(intf, node_filter):
    consumers = []
    _get_consumer_tree_rec(intf, consumers, node_filter)
    return consumers


def graph(path='/', root=None, node_filter=lambda x: x, outdir=None):
    top = find(path, root)
    v = Visitor(node_filter, outdir)
    v.visit(top)

    v.edge_map = {}

    for module, node in v.node_map.items():
        for pout in module.out_ports:
            edges = get_consumer_tree(pout.producer, node_filter)

            for e in edges:
                v.edge_map[e] = pydot.Edge(
                    node,
                    v.node_map[e.gear],
                    label=f"{pout.basename} -> {e.basename}")
                v.graph.add_edge(v.edge_map[e])

    return v
