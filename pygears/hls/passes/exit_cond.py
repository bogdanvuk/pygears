from .utils import HDLVisitor, ir, res_true


class InferInCond(HDLVisitor):
    def AssignValue(self, node):
        return node

    def BaseBlock(self, node):
        stmts = node.stmts
        node.stmts = []

        cur_block = node

        for stmt in stmts:
            cur_block.stmts.append(self.visit(stmt))

            if stmt.in_cond != res_true:
                cur_block.stmts.append(
                    ir.HDLBlock(in_cond=stmt.in_cond, stmts=[]))
                cur_block = cur_block.stmts[-1]

        return node

    # def IfElseBlock(self, node):
    #     exit_cond = res_true
    #     for child in reversed(node.stmts):
    #         self.visit(child)
    #         exit_cond = ir.ConditionalExpr((child.exit_cond, exit_cond),
    #                                        cond=child.opt_in_cond)

    #     node.exit_cond = exit_cond
    #     return node


class InferExitCond(HDLVisitor):
    def AssignValue(self, node):
        return node

    def BaseBlock(self, node):
        stmts = node.stmts
        node.stmts = []

        if isinstance(node, ir.HDLBlock):
            exit_cond = node.exit_cond
        else:
            exit_cond = res_true

        cur_block = node

        for stmt in stmts:
            cur_block.stmts.append(self.visit(stmt))

            if stmt.exit_cond != res_true or stmt.in_cond != res_true:
                next_in_cond = ir.BinOpExpr(
                    (ir.UnaryOpExpr(stmt.opt_in_cond, ir.opc.Not),
                     ir.BinOpExpr((stmt.in_cond, stmt.exit_cond), ir.opc.And)),
                    ir.opc.Or)

                cur_block.stmts.append(
                    ir.HDLBlock(in_cond=next_in_cond, stmts=[]))
                cur_block = cur_block.stmts[-1]

                if exit_cond == res_true:
                    exit_cond = next_in_cond
                else:
                    exit_cond = ir.BinOpExpr((exit_cond, next_in_cond),
                                             ir.opc.And)

        if isinstance(node, ir.HDLBlock):
            node.exit_cond = exit_cond

        return node

    def IfElseBlock(self, node):
        exit_cond = res_true
        for child in reversed(node.stmts):
            self.visit(child)
            exit_cond = ir.ConditionalExpr((child.exit_cond, exit_cond),
                                           cond=child.opt_in_cond)

        node.exit_cond = exit_cond
        return node


def infer_exit_cond(modblock, ctx):
    InferExitCond(ctx).visit(modblock)
    return modblock


def infer_in_cond(modblock, ctx):
    # InferInCond(ctx).visit(modblock)
    return modblock
