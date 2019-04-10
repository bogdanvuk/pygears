from .conditions import cond_name_match
from .inst_visit import InstanceVisitor


class ConditionCleanup(InstanceVisitor):
    def __init__(self, conds):
        self.conditions = conds

    def same_cond(self, find_cond):
        for cond in self.conditions:
            if cond.target == find_cond:
                if cond_name_match(cond.val):
                    new_cond = cond.val
                    if new_cond is None:
                        return None

                    while new_cond is not None:
                        last_cond = new_cond
                        new_cond = self.same_cond(last_cond)

                    return last_cond

        return None

    def enter_block(self, node):
        if getattr(node, 'in_cond', None):
            new_cond = self.same_cond(node.in_cond)
            if new_cond is not None:
                node.in_cond = new_cond

    def _simplify_assign(self, stmt, name=None):
        if name is None:
            name = stmt.target

        if stmt.width:
            return

        cond = self.same_cond(stmt.val)
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

    return hdl_stmts
