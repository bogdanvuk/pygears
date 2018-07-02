from cnncdp2lib.rd_addrgen import rd_addrgen, TCfg
from pygears.sim import seqr, drv, sim
from pygears.common import shred
from pygears.sim.extens.vcd import VCD
from pygears.sim.extens.activity_report import ActivityReporter

# from pygears.typing import Uint, Tuple, Unit, Queue

# t = Queue[Unit, 2]
# print(Unit())
# v = t((Unit(), False, True))
# print(v)

# import pydot
# graph = pydot.Dot(graph_type='digraph', rankdir='LR')
# rd_addrgen = pydot.Cluster(label='rd_addrgen')
# fmap1 = pydot.Node("fmap1")
# rnghop = pydot.Node("rnghop")
# rd_addrgen.add_node(fmap1)
# rd_addrgen.add_node(rnghop)
# graph.add_subgraph(rd_addrgen)
# graph.add_edge(pydot.Edge(fmap1, rnghop, label="dout -> din"))
# graph.add_edge(pydot.Edge(fmap1, rnghop, label="dout2 -> din1"))
# graph.write_png('proba.png')
# graph.write_dot('proba.dot')

print(TCfg.templates)

cfg_t = TCfg[dict(w_ifm=9, w_stride=4, w_kernel=4, w_pad=2)]

print(cfg_t.fields)
cfg = {
    'ifm_w': 8,
    'ifm_h': 8,
    'stride_x': 1,
    'stride_y': 1,
    'kernel_w': 3,
    'kernel_h': 3,
    'pad_lu': 1,
    'pad_rl': 1,
    'stride_x_p': 1,
    'stride_y_p': 1,
    'kernel_w_p': 1,
    'kernel_h_p': 1
}
seqr(t=cfg_t, seq=[cfg_t(cfg)]) \
    | drv \
    | rd_addrgen \
    | shred

from pygears.util.graphviz import graph
s = sim(outdir='/tmp/proba', extens=[VCD, ActivityReporter], vcd_include=['*'], run=False)

# g = graph()
# g.write_svg('proba.svg')
# g.write_pdf('proba.pdf')
# g.write_xdot('proba.xdot')
# g.write_png('proba.png')
# g.write_dot('proba.dot')

s.run()

