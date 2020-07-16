import ast
import sys
import types
import inspect
from functools import partial
from . import Context, HLSSyntaxError, node_visitor, ir, visit_ast, visit_block
from .arith import resolve_arith_func
from .call import resolve_func
from pygears.typing import cast, Integer


@node_visitor(ast.Expr)
def expr(node, ctx: Context):
    return visit_ast(node.value, ctx)


@node_visitor(ast.IfExp)
def parse_ifexp(node, ctx: Context):
    res = {field: visit_ast(getattr(node, field), ctx) for field in node._fields}

    if all(isinstance(v, ir.ResExpr) for v in res.values()):
        return ir.ResExpr(res['body'].val if res['test'].val else res['orelse'])

    return ir.ConditionalExpr(operands=(res['body'], res['orelse']), cond=res['test'])


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

            raise SyntaxError(f"Name '{node.id}' not found")

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
    return ir.SubscriptExpr(visit_ast(node.value, ctx), visit_ast(node.slice, ctx))


METHOD_OP_MAP = {
    ast.Add: '__add__',
    ast.And: '__and__',
    ast.BitAnd: '__and__',
    ast.BitOr: '__or__',
    ast.BitXor: '__xor__',
    ast.Div: '__truediv__',
    ast.Eq: '__eq__',
    ast.Gt: '__gt__',
    ast.GtE: '__ge__',
    ast.FloorDiv: '__floordiv__',
    ast.Lt: '__lt__',
    ast.LtE: '__le__',
    ast.LShift: '__lshift__',
    ast.MatMult: '__matmul__',
    ast.Mult: '__mul__',
    ast.Mod: '__mod__',
    ast.NotEq: '__ne__',
    ast.Not: '__not__',
    ast.Or: '__or__',
    ast.RShift: '__rshift__',
    ast.Sub: '__sub__',
    ast.UAdd: '__pos__',
    ast.USub: '__neg__',
}

R_METHOD_OP_MAP = {
    ast.Add: '__radd__',
    ast.BitAnd: '__rand__',
    ast.BitOr: '__ror__',
    ast.BitXor: '__rxor__',
    ast.Div: '__rtruediv__',
    ast.Eq: '__eq__',
    ast.Gt: '__le__',
    ast.GtE: '__lt__',
    ast.FloorDiv: '__rfloordiv__',
    ast.Lt: '__ge__',
    ast.LtE: '__gt__',
    ast.MatMult: '__rmatmul__',
    ast.Mult: '__rmul__',
    ast.Mod: '__rmod__',
    ast.NotEq: '__ne__',
    ast.Sub: '__rsub__'
}


def visit_bin_expr(op, operands, ctx: Context):
    op1 = visit_ast(operands[0], ctx)
    op2 = visit_ast(operands[1], ctx)

    if type(op) in [ast.And, ast.Or]:
        return ir.BinOpExpr((op1, op2), type(op))

    # TODO: This WAS needed, since: ir.ResExpr(Uint[8]).dtype is None. REMOVE
    dtype = type(op1.val) if isinstance(op1, ir.ResExpr) else op1.dtype
    # f = getattr(op1.dtype, METHOD_OP_MAP[type(op)])

    f = getattr(dtype, METHOD_OP_MAP[type(op)])

    ret = resolve_func(f, (op1, op2), {}, ctx)

    if ret != ir.ResExpr(NotImplemented):
        return ret

    # TODO: This WAS needed, since: ir.ResExpr(Uint[8]).dtype is None. REMOVE
    dtype = type(op2.val) if isinstance(op2, ir.ResExpr) else op2.dtype
    # f = getattr(op2.dtype, R_METHOD_OP_MAP[type(op)])

    f = getattr(dtype, R_METHOD_OP_MAP[type(op)])

    ret = resolve_func(f, (op2, op1), {}, ctx)

    return ret


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

    if isinstance(value, ir.ResExpr):
        return ir.ResExpr(getattr(value.val, node.attr))

    if hasattr(value.dtype, node.attr):
        try:
            cls_attr = object.__getattribute__(value.dtype, node.attr).func
        except Exception:
            cls_attr = getattr(value.dtype, node.attr)

        if isinstance(cls_attr, property):
            return resolve_func(cls_attr.fget, (value, ), {}, ctx)

        if not inspect.isclass(cls_attr):
            if callable(cls_attr):
                return ir.ResExpr(partial(cls_attr, value))

            # If value.attr was a class method and we instantly got the result
            return ir.ResExpr(cls_attr)

    return ir.AttrExpr(value, node.attr)


if sys.version_info[1] < 8:

    @node_visitor(ast.Str)
    def _(node, ctx: Context):
        return ir.ResExpr(node.s)

    @node_visitor(ast.NameConstant)
    def _(node, ctx: Context):
        return ir.ResExpr(node.value)

    @node_visitor(ast.Num)
    def num(node, ctx: Context):
        return ir.ResExpr(cast(node.n, Integer))

else:

    @node_visitor(ast.Constant)
    def _(node, ctx: Context):
        if isinstance(node.value, (int, float)):
            return ir.ResExpr(cast(node.n, Integer))
        else:
            return ir.ResExpr(node.value)


@node_visitor(ast.Index)
def _(node, ctx: Context):
    return visit_ast(node.value, ctx)


@node_visitor(ast.Slice)
def _(node, ctx: Context):
    return ir.SliceExpr(visit_ast(node.lower, ctx), visit_ast(node.upper, ctx),
                        visit_ast(node.step, ctx))


def py_eval_expr(node, ctx: Context):
    gear_locals = {n: v.val for n, v in ctx.scope.items() if isinstance(v, ir.ResExpr)}

    return eval(
        compile(ast.Expression(ast.fix_missing_locations(node)), filename="<ast>", mode="eval"),
        gear_locals, ctx.local_namespace)


@node_visitor(ast.DictComp)
def _(node, ctx: Context):
    return ir.ResExpr(py_eval_expr(node, ctx))


@node_visitor(ast.ListComp)
def _(node, ctx: Context):
    return ir.ResExpr(py_eval_expr(node, ctx))


@node_visitor(ast.List)
def _(node: ast.List, ctx: Context):
    return ir.ResExpr(ir.ConcatExpr([visit_ast(e, ctx) for e in node.elts]))
