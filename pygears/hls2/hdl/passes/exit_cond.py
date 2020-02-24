from .utils import HDLVisitor, nodes, pydl, res_true

class RewriteExitCond(HDLVisitor):
    def AssignValue(self, node):
        return node

    def BaseBlock(self, node):
        stmts = node.stmts
        node.stmts = []

        if isinstance(node, nodes.HDLBlock):
            exit_cond = node.exit_cond
        else:
            exit_cond = res_true

        cur_block = node

        for stmt in stmts:
            cur_block.stmts.append(self.visit(stmt))

            if stmt.exit_cond != res_true or stmt.in_cond != res_true:
                next_in_cond = pydl.BinOpExpr(
                    (pydl.UnaryOpExpr(stmt.opt_in_cond, pydl.opc.Not),
                     pydl.BinOpExpr(
                         (stmt.in_cond, stmt.exit_cond), pydl.opc.And)),
                    pydl.opc.Or)

                cur_block.stmts.append(
                    nodes.HDLBlock(in_cond=next_in_cond, stmts=[], dflts={}))
                cur_block = cur_block.stmts[-1]

                if exit_cond == res_true:
                    exit_cond = next_in_cond
                else:
                    exit_cond = pydl.BinOpExpr((exit_cond, next_in_cond),
                                               pydl.opc.And)

        if isinstance(node, nodes.HDLBlock):
            node.exit_cond = exit_cond

        return node

    def IfElseBlock(self, node):
        exit_cond = res_true
        for child in reversed(node.stmts):
            self.visit(child)
            exit_cond = pydl.ConditionalExpr((child.exit_cond, exit_cond),
                                             cond=child.opt_in_cond)

        node.exit_cond = exit_cond
        return node


def infer_exit_cond(modblock, ctx):
    RewriteExitCond(ctx).visit(modblock)
    return modblock
