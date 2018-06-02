from pygears.core.hier_node import HierVisitorBase


class RTLConnectVisitor(HierVisitorBase):
    def HierNode(self, rtl_gear):
        super().HierNode(rtl_gear)
        if hasattr(rtl_gear, 'connect'):
            rtl_gear.connect()


def rtl_connect(top, conf):
    v = RTLConnectVisitor()
    v.visit(top)
    # for rtl_gear in top.child:
    #     v.visit(rtl_gear)

    return top.node
