import pydot
from pygears.core.port import InPort
from pygears.core.hier_node import HierVisitorBase
from pygears.util.find import find


class Visitor(HierVisitorBase):
    def __init__(self, node_filter):
        self.dot = GearGraph(graph_type='digraph', rankdir='TB', overlap=True)

        self.hier = [self.dot]
        self.node_filter = node_filter

    def enter_hier(self, module):
        self.hier.append(self.dot.cluster_map[module])

    def exit_hier(self, module):
        node = self.hier.pop()
        self.hier[-1].add_subgraph(node)

    def Gear(self, module):
        if self.node_filter(module):
            self.dot.node_map[module] = pydot.Node(
                module.name,
                fontsize=18,
                margin=0.01,
                tooltip=module.name,
                label=module.basename,
                shape="doubleoctagon")

            self.hier[-1].add_node(self.dot.node_map[module])
        else:
            self.dot.cluster_map[module] = pydot.Cluster(
                graph_name=module.name,
                label=module.basename,
                tooltip=module.name,
                fontsize=48,
                fontcolor='blue',
                labeljust='l',
                overlap=False)

            self.enter_hier(module)

            super().HierNode(module)

            self.exit_hier(module)

        return True


class GearGraph(pydot.Dot):
    def __init__(self, *argsl, **argsd):
        super().__init__(*argsl, **argsd)
        self._node_map = {}
        self._cluster_map = {}
        self._prod_edge_map = {}
        self._cons_edge_map = {}

    @property
    def node_map(self):
        return self._node_map

    @property
    def cluster_map(self):
        return self._cluster_map

    @property
    def prod_edge_map(self):
        return self._prod_edge_map

    @property
    def cons_edge_map(self):
        return self._cons_edge_map


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


def graph(top=None,
          node_filter=lambda x: not x.child,
          edge_fmt='{prod_gear} -> {cons_gear}'):
    if top is None:
        top = find('/')

    v = Visitor(node_filter)
    v.visit(top)

    edge_fmt_dict = {}

    dot = v.dot

    for module, node in dot.node_map.items():
        for pout in module.out_ports:
            edge_fmt_dict['prod_port'] = pout.basename
            edge_fmt_dict['prod_gear'] = pout.gear.basename

            if getattr(pout.consumer, 'var_name', None):
                edge_fmt_dict['prod_var'] = pout.consumer.var_name
            else:
                edge_fmt_dict['prod_var'] = edge_fmt_dict['prod_gear']

            edges = get_consumer_tree(pout.producer, node_filter)

            dot.prod_edge_map[pout] = []

            for e in edges:
                edge_fmt_dict['cons_port'] = e.basename
                edge_fmt_dict['cons_gear'] = e.gear.basename
                if getattr(e.producer, 'var_name', None):
                    edge_fmt_dict['cons_var'] = e.producer.var_name
                else:
                    edge_fmt_dict['cons_var'] = edge_fmt_dict['cons_gear']

                dot_edge = pydot.Edge(
                    node,
                    dot.node_map[e.gear],
                    fontsize=20,
                    decoreate=True,
                    label=eval(f'f"{edge_fmt}"', globals(), edge_fmt_dict))

                dot.cons_edge_map[e] = dot_edge
                dot.prod_edge_map[pout].append(dot_edge)
                dot.add_edge(dot_edge)

    return dot
