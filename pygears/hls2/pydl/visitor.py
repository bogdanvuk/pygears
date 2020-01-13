import inspect
from . import nodes


class PydlVisitor:
    def visit(self, node, **kwds):
        method = 'visit_' + node.__class__.__name__
        visitor = getattr(self, method, self.generic_visit)

        if visitor.__name__ == 'generic_visit' and isinstance(node, nodes.Block):
            visitor = getattr(self, 'visit_all_Block', self.generic_visit)

        if visitor.__name__ == 'generic_visit' and isinstance(node, nodes.Expr):
            visitor = getattr(self, 'visit_all_Expr', self.generic_visit)

        if visitor.__name__ == 'generic_visit' and isinstance(node, nodes.Statement):
            visitor = getattr(self, 'visit_all_Statement', self.generic_visit)

        if kwds:
            sig = inspect.signature(visitor)

        if kwds and ('kwds' in sig.parameters):
            return visitor(node, **kwds)

        return visitor(node)

    def generic_visit(self, node):
        raise Exception(
            f'Method "{node.__class__.__name__}" not implemented in "{self.__class__.__name__}" visitor')


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
        val = self.visit(node.val)
        if val is not None:
            return nodes.AttrExpr(val, node.attr)

        return node

    def visit_CastExpr(self, node):
        operand = self.visit(node.operand)
        if operand is not None:
            return nodes.CastExpr(operand, node.cast_to)

        return node

    def visit_ConcatExpr(self, node):
        ops = [self.visit(op) for op in node.operands]
        if all(op is None for op in ops):
            return node

        ops = [
            old_op if new_op is None else new_op
            for new_op, old_op in zip(ops, node.operands)
        ]

        return nodes.ConcatExpr(tuple(ops))

    def visit_ArrayOpExpr(self, node):
        array = self.visit(node.array)
        if array is not None:
            return nodes.ArrayOpExpr(array, node.operator)

        return node

    def visit_UnaryOpExpr(self, node):
        operand = self.visit(node.operand)
        if operand is not None:
            return nodes.UnaryOpExpr(operand, node.operator)

        return node

    def visit_BinOpExpr(self, node):
        ops = [self.visit(op) for op in node.operands]
        if all(op is None for op in ops):
            return node

        ops = [
            old_op if new_op is None else new_op
            for new_op, old_op in zip(ops, node.operands)
        ]

        return nodes.BinOpExpr(tuple(ops), node.operator)

    def visit_SubscriptExpr(self, node):
        old_ops = (node.val, node.index)

        ops = [self.visit(op) for op in old_ops]
        if all(op is None for op in ops):
            return node

        ops = [
            old_op if new_op is None else new_op for new_op, old_op in zip(ops, old_ops)
        ]

        return nodes.SubscriptExpr(*ops)

    def visit_ConditionalExpr(self, node):
        old_ops = (node.cond, *node.operands)

        ops = [self.visit(op) for op in old_ops]
        if all(op is None for op in ops):
            return node

        ops = [
            old_op if new_op is None else new_op for new_op, old_op in zip(ops, old_ops)
        ]

        return nodes.ConditionalExpr(tuple(ops[1:]), ops[0])

    def generic_visit(self, node):
        return node
