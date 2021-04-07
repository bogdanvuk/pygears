from pygears.hls.cfg import Node, CfgDfs, forwardlink
from pygears.hls import ir
from pygears.hls.passes.schedule import draw_scheduled_cfg


def test_mid_dfs():

    b = Node(ir.Module())
    hdl = Node(ir.HDLBlock(), prev=[b])
    b1 = Node(ir.Branch(), prev=[hdl])
    b2 = Node(ir.Branch(), prev=[hdl])
    e1 = Node(ir.ExprStatement('e1'), prev=[b1])
    e2 = Node(ir.ExprStatement('e2'), prev=[b2])
    s1 = Node(ir.BranchSink(), prev=[e1], source=b2)
    s2 = Node(ir.BranchSink(), prev=[e2], source=b2)
    hdls = Node(ir.HDLBlockSink(), prev=[s1, s2], source=hdl)
    e3 = Node(ir.ExprStatement('e3'), prev=[hdls])
    sink = Node(ir.ModuleSink(), prev=[e3], source=b)

    forwardlink(sink)

    class Trail(CfgDfs):
        def __init__(self):
            self.trail = []
            super().__init__()

        def enter_BaseBlockSink(self, node):
            if node.source in self.trail:
                self.trail.append(node)

        def enter_HDLBlockSink(self, node):
            if node.source in self.trail:
                self.trail.append(node)

        def enter_Statement(self, node):
            self.trail.append(node)

    v = Trail()
    v.visit(e1)
    assert (v.trail == [e1, e3])
    # for n in v.trail:
    #     print(str(n.value))

    # draw_scheduled_cfg(b, simple=False)
