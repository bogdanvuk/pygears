import inspect
from . import nodes


class PydlVisitor:
    def visit(self, node, **kwds):
        method = 'visit_' + node.__class__.__name__
        visitor = getattr(self, method, self.generic_visit)

        if visitor.__name__ == 'generic_visit' and isinstance(
                node, nodes.Block):
            visitor = getattr(self, 'visit_all_Block', self.generic_visit)

        if visitor.__name__ == 'generic_visit' and isinstance(
                node, nodes.Expr):
            visitor = getattr(self, 'visit_all_Expr', self.generic_visit)

        if visitor.__name__ == 'generic_visit' and isinstance(
                node, nodes.Statement):
            visitor = getattr(self, 'visit_all_Statement', self.generic_visit)

        if kwds:
            sig = inspect.signature(visitor)

        if kwds and ('kwds' in sig.parameters):
            return visitor(node, **kwds)

        return visitor(node)

    def generic_visit(self, node):
        raise Exception(
            f'Method "{node.__class__.__name__}" not implemented in "{self.__class__.__name__}" visitor'
        )


class PydlExprVisitor:
    def visit(self, node):
        method = 'visit_' + node.__class__.__name__
        visitor = getattr(self, method, self.generic_visit)
        return visitor(node)

    def visit_AttrExpr(self, node):
        self.visit(node.val)

    def visit_CastExpr(self, node):
        self.visit(node.operand)

    def visit_ConcatExpr(self, node):
        for op in node.operands:
            self.visit(op)

    def visit_ArrayOpExpr(self, node):
        self.visit(node.array)

    def visit_UnaryOpExpr(self, node):
        self.visit(node.operand)

    def visit_BinOpExpr(self, node):
        for op in node.operands:
            self.visit(op)

    def visit_SubscriptExpr(self, node):
        self.visit(node.val)
        self.visit(node.index)

    def visit_ConditionalExpr(self, node):
        self.visit(node.cond)
        for op in node.operands:
            self.visit(op)

    def generic_visit(self, node):
        pass


class PydlExprRewriter:
    def visit(self, node):
        method = 'visit_' + node.__class__.__name__
        visitor = getattr(self, method, self.generic_visit)
        return visitor(node)

    def visit_AttrExpr(self, node):
        return nodes.AttrExpr(self.visit(node.val), node.attr)

    def visit_CastExpr(self, node):
        return nodes.CastExpr(self.visit(node.operand), node.cast_to)

    def visit_ConcatExpr(self, node):
        return nodes.ConcatExpr(tuple(self.visit(op) for op in node.operands))

    def visit_ArrayOpExpr(self, node):
        return nodes.ArrayOpExpr(self.visit(node.array), node.operator)

    def visit_UnaryOpExpr(self, node):
        return nodes.UnaryOpExpr(self.visit(node.operand), node.operator)

    def visit_BinOpExpr(self, node):
        return nodes.BinOpExpr(tuple(self.visit(op) for op in node.operands),
                               node.operator)

    def visit_SubscriptExpr(self, node):
        return nodes.SubscriptExpr(self.visit(node.val),
                                   self.visit(node.index))

    def visit_ConditionalExpr(self, node):
        return nodes.ConditionalExpr(
            self.visit(node.cond),
            tuple(self.visit(op) for op in node.operands))

    def generic_visit(self, node):
        return node
