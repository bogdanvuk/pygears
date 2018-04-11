from pygears.core.hier_node import HierVisitorBase


class SVGenConnectVisitor(HierVisitorBase):
    def HierNode(self, svmod):
        super().HierNode(svmod)
        if hasattr(svmod, 'connect'):
            svmod.connect()


# class SVGenPortFreezeVisitor(HierVisitorBase):
#     def SVGenNodeBase(self, svmod):
#         super().HierNode(svmod)
#         svmod.in_ports = 


def svgen_connect(top, conf):
    v = SVGenConnectVisitor()
    v.visit(top)
    # f = SVGenPortFreezeVisitor()
    # f.visit(top)
    return top
