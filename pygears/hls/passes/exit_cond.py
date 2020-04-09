from ..ir_utils import HDLVisitor, ir, res_true


class InferInCond(HDLVisitor):
    def AssignValue(self, node):
        return node

    def BaseBlock(self, node):
        stmts = node.stmts
        node.stmts = []

        cur_block = node

        for stmt in stmts:
            cur_block.stmts.append(self.visit(stmt))

            if stmt.in_await != res_true:
                cur_block.stmts.append(
                    ir.HDLBlock(in_cond=stmt.in_await, stmts=[]))
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
    def __init__(self, ctx):
        self.ctx = ctx
        self.block_stack = []

    @property
    def block(self):
        if not self.block_stack:
            return None

        return self.block_stack[-1]

    def AssignValue(self, node):
        return node

    def BaseBlock(self, node):
        stmts = node.stmts
        node.stmts = []

        exit_cond = res_true
        cur_block = node

        self.block_stack.append(node)
        for stmt in stmts:
            cur_block.stmts.append(self.visit(stmt))

            if isinstance(stmt, ir.HDLBlock):
                next_in_cond = ir.BinOpExpr(
                    (ir.UnaryOpExpr(stmt.in_cond, ir.opc.Not), stmt.exit_cond),
                    ir.opc.Or)
            elif stmt.exit_await != res_true or stmt.in_await != res_true:
                next_in_cond = ir.BinOpExpr((stmt.in_await, stmt.exit_await),
                                            ir.opc.And)

            else:
                continue

            if exit_cond == res_true:
                exit_cond = next_in_cond
            else:
                exit_cond = ir.BinOpExpr((exit_cond, next_in_cond), ir.opc.And)

            cur_block.stmts.append(ir.HDLBlock(in_cond=next_in_cond, stmts=[]))
            cur_block = cur_block.stmts[-1]

        self.block_stack.pop()

        if isinstance(node, ir.HDLBlock):
            node.exit_cond = ir.BinOpExpr((exit_cond, node.exit_cond), ir.opc.And)

        return node

    def IfElseBlock(self, node):
        exit_cond = res_true

        self.block_stack.append(node)

        for child in reversed(node.stmts):
            self.visit(child)
            exit_cond = ir.ConditionalExpr((child.exit_cond, exit_cond),
                                           cond=child.in_cond)

        self.block_stack.pop()

        node.exit_cond = exit_cond
        return node


def infer_exit_cond(modblock, ctx):
    InferExitCond(ctx).visit(modblock)
    return modblock


def infer_in_cond(modblock, ctx):
    # InferInCond(ctx).visit(modblock)
    return modblock
