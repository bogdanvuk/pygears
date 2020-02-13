from ..pydl import nodes as pydl
from .nodes import HDLBlock
from pygears.typing import Bool

res_true = pydl.ResExpr(Bool(True))
res_false = pydl.ResExpr(Bool(False))


class HDLVisitor:
    def __init__(self, ctx):
        self.ctx = ctx

    def visit(self, node):
        method = 'visit_' + node.__class__.__name__
        visitor = getattr(self, method, self.generic_visit)

        return visitor(node)

    def generic_visit(self, node):
        return node


class RewriteExitCond(HDLVisitor):
    def visit_AssignValue(self, node):
        return node

    def generic_visit(self, node):
        stmts = node.stmts
        node.stmts = []

        exit_cond = node.exit_cond
        cur_block = node

        for stmt in stmts:
            cur_block.stmts.append(self.visit(stmt))

            if stmt.exit_cond != res_true:
                next_in_cond = pydl.BinOpExpr(
                    (pydl.UnaryOpExpr(stmt.opt_in_cond, pydl.opc.Not),
                     pydl.BinOpExpr(
                         (stmt.in_cond, stmt.exit_cond), pydl.opc.And)),
                    pydl.opc.Or)

                cur_block.stmts.append(
                    HDLBlock(in_cond=next_in_cond, stmts=[], dflts={}))
                cur_block = cur_block.stmts[-1]

                if exit_cond == res_true:
                    exit_cond = next_in_cond
                else:
                    exit_cond = pydl.BinOpExpr((exit_cond, next_in_cond),
                                               pydl.opc.And)

        node.exit_cond = exit_cond

        return node

    def visit_IfElseBlock(self, node):
        exit_cond = res_true
        for child in reversed(node.stmts):
            self.visit(child)
            exit_cond = pydl.ConditionalExpr((child.exit_cond, exit_cond),
                                             cond=child.opt_in_cond)

        node.exit_cond = exit_cond
        return node


class RemoveDeadCode(HDLVisitor):
    def visit_AssignValue(self, node):
        return node

    def generic_visit(self, node):
        stmts = node.stmts
        live_stmts = []

        if (node.opt_in_cond == res_false) or (node.in_cond == res_false):
            return None

        for stmt in stmts:
            child = self.visit(stmt)
            if child is not None:
                live_stmts.append(child)

        if not node.stmts:
            return None

        node.stmts = live_stmts

        return node


class InlineValues(HDLVisitor):
    def visit_AssignValue(self, node):
        return node

    def generic_visit(self, node):
        pass
