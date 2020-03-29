from .utils import IrExprRewriter, IrRewriter
from pygears.core.datagear import is_datagear
from ..ast.inline import call_datagear


class CallExprRewriter(IrExprRewriter):
    def __init__(self, ctx):
        self.ctx = ctx

    def visit_CallExpr(self, expr):
        if is_datagear(expr.func):
            return call_datagear(expr.func, expr.args, expr.params, self.ctx)
        else:
            return expr
            # intf, stmts = call_gear(func, *form_gear_args(args, kwds, func), ctx)
            # ctx.pydl_parent_block.stmts.extend(stmts)
            # return intf


class ExprFinder(IrRewriter):
    def __init__(self, ctx):
        self.ctx = ctx

    def Expr(self, expr):
        return CallExprRewriter(self.ctx).visit(expr)


def resolve_gear_calls(modblock, ctx):
    modblock = ExprFinder(ctx).visit(modblock)

    return modblock
