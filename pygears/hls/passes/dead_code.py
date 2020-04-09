from ..ir_utils import HDLVisitor, add_to_list, ir, res_false

class RemoveDeadCode(HDLVisitor):
    def AssignValue(self, node):
        return node

    def FuncReturn(self, node):
        return node

    def BaseBlock(self, block: ir.BaseBlock):
        stmts = []
        for stmt in block.stmts:
            add_to_list(stmts, self.visit(stmt))

        block.stmts = stmts
        return block

    # def ExprStatement(self, stmt: ir.ExprStatement):
    #     return None

    # TODO: Implement things properly for IfElseBlock (What if middle elif is missing?)

    def HDLBlock(self, node):
        stmts = node.stmts
        live_stmts = []

        if node.in_cond == res_false:
            return None

        for stmt in stmts:
            child = self.visit(stmt)
            if child is not None:
                live_stmts.append(child)

        if not node.stmts:
            return None

        node.stmts = live_stmts

        return node


def remove_dead_code(modblock, ctx):
    RemoveDeadCode(ctx).visit(modblock)
    return modblock
