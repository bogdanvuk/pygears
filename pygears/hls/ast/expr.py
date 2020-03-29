import ast
import types
from . import Context, SyntaxError, node_visitor, ir, visit_ast, visit_block
from .arith import resolve_arith_func
from pygears.typing import cast, Integer


@node_visitor(ast.Expr)
def expr(node, ctx: Context):
    return visit_ast(node.value, ctx)


@node_visitor(ast.IfExp)
def parse_ifexp(node, ctx: Context):
    res = {
        field: visit_ast(getattr(node, field), ctx)
        for field in node._fields
    }

    if all(isinstance(v, ir.ResExpr) for v in res.values()):
        return ir.ResExpr(
            res['body'].val if res['test'].val else res['orelse'])

    return ir.ConditionalExpr(operands=(res['body'], res['orelse']),
                              cond=res['test'])


@node_visitor(ast.Num)
def num(node, ctx: Context):
    return ir.ResExpr(cast(node.n, Integer))


@node_visitor(ast.Name)
def _(node: ast.Name, ctx: Context):
    if isinstance(node.ctx, ast.Load):
        if node.id not in ctx.scope:
            if node.id in ctx.local_namespace:
                return ir.ResExpr(ctx.local_namespace[node.id])

            builtins = ctx.local_namespace['__builtins__']
            if not isinstance(builtins, dict):
                builtins = builtins.__dict__

            if node.id in builtins:
                return ir.ResExpr(builtins[node.id])

            raise SyntaxError(f"Name '{node.id}' not found", node.lineno)

        if isinstance(ctx.scope[node.id], ir.ResExpr):
            return ctx.scope[node.id]

        return ctx.ref(node.id, ctx='load')

    if isinstance(node.ctx, ast.Store):
        if node.id in ctx.scope:
            return ctx.ref(node.id, ctx='store')

        return ir.Name(node.id, None, 'store')


@node_visitor(ast.UnaryOp)
def _(node: ast.UnaryOp, ctx: Context):
    operand = visit_ast(node.operand, ctx)
    # if operand is None:
    #     return None

    return ir.UnaryOpExpr(operand, type(node.op))


@node_visitor(ast.Tuple)
def _(node, ctx: Context):
    return ir.ConcatExpr([visit_ast(item, ctx) for item in node.elts])


@node_visitor(ast.Subscript)
def _(node, ctx: Context):
    return ir.SubscriptExpr(visit_ast(node.value, ctx),
                            visit_ast(node.slice, ctx))


def visit_bin_expr(op, operands, ctx: Context):
    res = resolve_arith_func(op, tuple(visit_ast(p, ctx) for p in operands),
                             ctx)
    return res

    # if isinstance(res, FunctionType):
    #     return resolve_func_call(res, res.__name__, opexp, None, operands,
    #                              module_data)
    # else:
    #     return res


@node_visitor(ast.Compare)
def _(node, ctx: Context):
    return visit_bin_expr(node.ops[0], (node.left, node.comparators[0]), ctx)


@node_visitor(ast.BoolOp)
def _(node, ctx: Context):
    return visit_bin_expr(node.op, (node.values[0], node.values[1]), ctx)


@node_visitor(ast.BinOp)
def _(node, ctx: Context):
    return visit_bin_expr(node.op, (node.left, node.right), ctx)


@node_visitor(ast.Attribute)
def _(node, ctx: Context):
    value = visit_ast(node.value, ctx)
    if isinstance(value, ir.Name) and isinstance(value.obj, ir.Interface):
        return ir.ResExpr(value.obj.intf.dtype)

    return ir.AttrExpr(value, node.attr)


@node_visitor(ast.Str)
def _(node, ctx: Context):
    return ir.ResExpr(node.s)


@node_visitor(ast.NameConstant)
def _(node, ctx: Context):
    return ir.ResExpr(node.value)


@node_visitor(ast.Index)
def _(node, ctx: Context):
    return visit_ast(node.value, ctx)


@node_visitor(ast.Slice)
def _(node, ctx: Context):
    return ir.SliceExpr(visit_ast(node.lower, ctx), visit_ast(node.upper, ctx),
                        visit_ast(node.step, ctx))


def py_eval_expr(node, ctx: Context):
    gear_locals = {
        n: v.val
        for n, v in ctx.scope.items() if isinstance(v, ir.ResExpr)
    }

    return eval(
        compile(ast.Expression(ast.fix_missing_locations(node)),
                filename="<ast>",
                mode="eval"), gear_locals, ctx.local_namespace)


@node_visitor(ast.DictComp)
def _(node, ctx: Context):
    return ir.ResExpr(py_eval_expr(node, ctx))


@node_visitor(ast.ListComp)
def _(node, ctx: Context):
    return ir.ResExpr(py_eval_expr(node, ctx))


@node_visitor(ast.List)
def _(node: ast.List, ctx: Context):
    return ir.ResExpr(ir.ConcatExpr([visit_ast(e, ctx) for e in node.elts]))
