import pydot
from pygears.core.hier_node import HierVisitorBase
from pygears.util.find import find
from pygears import registry


class Visitor(HierVisitorBase):
    def __init__(self):
        self.gear_map = {}
        self.node_map = {}
        self.graph = pydot.Dot(graph_type='digraph', rankdir='LR', overlap=False)
        self.hier = [self.graph]
        self.sim_map = registry('SimMap')

    def enter_hier(self, module):
        self.gear_map[module] = pydot.Cluster(graph_name=module.name, label=module.basename, fontsize=48, fontcolor='blue', labeljust='l', overlap=False)
        self.hier.append(self.gear_map[module])

    def exit_hier(self, module):
        node = self.hier.pop()
        self.hier[-1].add_subgraph(node)


    def Gear(self, module):
        if module in self.sim_map:
            self.gear_map[module] = pydot.Node(module.name, label = module.basename)
            self.node_map[module] = self.gear_map[module]
            self.hier[-1].add_node(self.gear_map[module])
        else:
            self.enter_hier(module)

            super().HierNode(module)

            self.exit_hier(module)

        return True


def graph(path='/', root=None):
    top = find(path, root)
    v = Visitor()
    v.visit(top)

    for module, node in v.node_map.items():
        for pout in module.out_ports:
            edges = pout.producer.end_consumers

            for e in edges:
                v.graph.add_edge(
                    pydot.Edge(node, v.node_map[e.gear], label=f"{pout.basename} -> {e.basename}"))

    return v
