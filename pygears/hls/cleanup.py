from .conditions import cond_name_match
from .inst_visit import InstanceVisitor


class ConditionExprCleanup(InstanceVisitor):
    def __init__(self, conds):
        self.conditions = conds

    def visit_str(self, node):
        for cond in self.conditions:
            if cond.target == node:
                if cond_name_match(cond.val):
                    new_cond = cond.val
                    if new_cond is None:
                        return None

                    while new_cond is not None:
                        last_cond = new_cond
                        new_cond = self.visit(last_cond)

                    return last_cond

        return None

    def generic_visit(self, node):
        pass

    def visit_UnaryOpExpr(self, node):
        operand = self.visit(node.operand)
        if operand is not None:
            breakpoint()
            node.operand = operand
            return node
        return None

    def visit_BinOpExpr(self, node):
        operands = []
        for op in node.operands:
            operands.append(self.visit(op))

        if any(operands):
            for i in range(len(operands)):
                if operands[i] is None:
                    operands[i] = node.operands[i]
            node.operands = tuple(operands)
            return node

        return None


class ConditionCleanup(InstanceVisitor):
    def __init__(self, conds):
        self.clean_expr = ConditionExprCleanup(conds).visit

    def enter_block(self, node):
        if getattr(node, 'in_cond', None):
            new_cond = self.clean_expr(node.in_cond)
            if new_cond is not None:
                node.in_cond = new_cond

    def _simplify_assign(self, stmt, name=None):
        if name is None:
            name = stmt.target

        if stmt.width:
            return

        cond = self.clean_expr(stmt.val)
        if cond is not None:
            stmt.val = cond

    def visit_AssertValue(self, node):
        pass

    def visit_HDLBlock(self, node):
        self.enter_block(node)

        for name, val in node.dflts.items():
            self._simplify_assign(val, name)

        for stmt in node.stmts:
            self.visit(stmt)

    def visit_CombSeparateStmts(self, node):
        for stmt in node.stmts:
            self._simplify_assign(stmt)

    def visit_CombBlock(self, node):
        self.visit_HDLBlock(node)

    def visit_AssignValue(self, node):
        self._simplify_assign(node)


def condition_cleanup(hdl_stmts):
    conditions = hdl_stmts[
        'conditions'].stmts if 'conditions' in hdl_stmts else []

    for _, val in hdl_stmts.items():
        ConditionCleanup(conditions).visit(val)

    if conditions:
        hdl_stmts['conditions'].stmts = [
            c for c in conditions
            if not cond_name_match(c.val) or c.target == 'rst_cond'
        ]

    return hdl_stmts
