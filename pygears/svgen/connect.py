from pygears.core.hier_node import HierVisitorBase


class SVGenConnectVisitor(HierVisitorBase):
    def HierNode(self, svmod):
        super().HierNode(svmod)
        if hasattr(svmod, 'connect'):
            svmod.connect()


def svgen_connect(top):
    v = SVGenConnectVisitor()
    v.visit(top)
