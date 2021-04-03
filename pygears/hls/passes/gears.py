from ..ir_utils import IrExprRewriter, IrRewriter
from pygears.core.datagear import is_datagear


class CallExprRewriter(IrExprRewriter):
    def __init__(self, ctx):
        self.ctx = ctx

    def visit_CallExpr(self, expr):
        if is_datagear(expr.func):
            breakpoint()
            # return call_datagear(expr.func, expr.args, expr.params, self.ctx)
        else:
            return expr


class ExprFinder(IrRewriter):
    def __init__(self, ctx):
        self.ctx = ctx
        super().__init__()

    def Expr(self, expr):
        return CallExprRewriter(self.ctx).visit(expr)


def resolve_gear_calls(modblock, ctx):
    modblock = ExprFinder(ctx).visit(modblock)

    return modblock
