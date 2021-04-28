import ast
import sys
import types
import inspect
from functools import partial
from . import Context, HLSSyntaxError, node_visitor, ir, visit_ast, visit_block
from .arith import resolve_arith_func
from .call import resolve_func, const_func_args
from .stmt import output_port_shadow_check
from pygears.typing import cast, Integer, typeof


@node_visitor(ast.Expr)
def expr(node, ctx: Context):
    return visit_ast(node.value, ctx)


@node_visitor(ast.IfExp)
def parse_ifexp(node, ctx: Context):
    test = visit_ast(node.test, ctx)

    if isinstance(test, ir.ResExpr):
        if test.val:
            return visit_ast(node.body, ctx)
        else:
            return visit_ast(node.orelse, ctx)

    body = visit_ast(node.body, ctx)
    orelse = visit_ast(node.orelse, ctx)

    return ir.ConditionalExpr(operands=(body, orelse), cond=test)


# TODO: Signal use of reserved names. Also use of output port names (Or mangle them?)
@node_visitor(ast.Name)
def _(node: ast.Name, ctx: Context):
    if isinstance(node.ctx, ast.Load):
        if (node.id in ctx.alias_map and isinstance(ctx.alias_map[node.id], ir.ResExpr)
                and node.id not in ctx.registers):
            return ctx.alias_map[node.id]

        if node.id not in ctx.scope:
            if node.id in ctx.local_namespace:
                return ir.ResExpr(ctx.local_namespace[node.id])

            builtins = ctx.local_namespace['__builtins__']
            if not isinstance(builtins, dict):
                builtins = builtins.__dict__

            if node.id in builtins:
                return ir.ResExpr(builtins[node.id])

            raise SyntaxError(f"Name '{node.id}' not found")

        return ctx.ref(node.id, ctx='load')

    elif isinstance(node.ctx, ast.Store):
        if node.id in ctx.scope:
            return ctx.ref(node.id, ctx='store')

        return ir.Name(node.id, None, 'store')


@node_visitor(ast.UnaryOp)
def _(node: ast.UnaryOp, ctx: Context):
    operand = visit_ast(node.operand, ctx)

    if type(node.op) in [ast.Not]:
        return ir.UnaryOpExpr(operand, type(node.op))

    # TODO: This WAS needed, since: ir.ResExpr(Uint[8]).dtype is None. REMOVE
    dtype = type(operand.val) if isinstance(operand, ir.ResExpr) else operand.dtype
    # f = getattr(operand.dtype, METHOD_OP_MAP[type(op)])

    f = getattr(dtype, METHOD_OP_MAP[type(node.op)])

    ret = resolve_func(f, (operand, ), {}, ctx)

    if ret != ir.ResExpr(NotImplemented):
        return ret

    raise SyntaxError(f"Operator '{ir.OPMAP[type(node.op)]}' not supported for operand of type "
                      f"{operand.dtype!r}")


@node_visitor(ast.Tuple)
def _(node, ctx: Context):
    return ir.ConcatExpr([visit_ast(item, ctx) for item in node.elts])


@node_visitor(ast.Subscript)
def _(node, ctx: Context):
    expr_ctx = 'load' if isinstance(node.ctx, ast.Load) else 'store'
    return ir.SubscriptExpr(visit_ast(node.value, ctx), visit_ast(node.slice, ctx), expr_ctx)


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
    ast.Invert: '__invert__',
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
    ast.In: '__contains__',
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

    # TODO: This WAS needed, since: ir.ResExpr(Uint[8]).dtype is None. REMOVE
    dtype = type(op1.val) if isinstance(op1, ir.ResExpr) else op1.dtype
    # f = getattr(op1.dtype, METHOD_OP_MAP[type(op)])

    if type(op) in METHOD_OP_MAP:
        f = getattr(dtype, METHOD_OP_MAP[type(op)])

        ret = resolve_func(f, (op1, op2), {}, ctx)

        if ret != ir.ResExpr(NotImplemented):
            return ret

    # TODO: This WAS needed, since: ir.ResExpr(Uint[8]).dtype is None. REMOVE
    dtype = type(op2.val) if isinstance(op2, ir.ResExpr) else op2.dtype
    # f = getattr(op2.dtype, R_METHOD_OP_MAP[type(op)])

    f = getattr(dtype, R_METHOD_OP_MAP[type(op)])

    ret = resolve_func(f, (op2, op1), {}, ctx)

    if ret != ir.ResExpr(NotImplemented):
        return ret

    raise SyntaxError(f"Operator '{ir.OPMAP[type(op)]}' not supported for operands of types "
                      f"{op1.dtype!r} and {op2.dtype!r}")


@node_visitor(ast.Compare)
def _(node, ctx: Context):
    left = node.left
    exprs = []
    for op, c in zip(node.ops, node.comparators):
        exprs.append(visit_bin_expr(op, (left, c), ctx))
        left = c

    if len(exprs) == 1:
        return exprs[0]
    else:
        return ir.BinOpExpr(exprs, ir.opc.And)


@node_visitor(ast.BoolOp)
def _(node, ctx: Context):
    ops = [visit_ast(opi, ctx) for opi in node.values]

    base = ir.BinOpExpr((ops[0], ops[1]), type(node.op))

    for op in ops[2:]:
        base = ir.BinOpExpr((base, op), type(node.op))

    return base


@node_visitor(ast.BinOp)
def _(node, ctx: Context):
    return visit_bin_expr(node.op, (node.left, node.right), ctx)


def get_dict_attr(obj, attr):
    for cls in (obj, ) + inspect.getmro(obj.__class__):
        if attr in cls.__dict__:
            if cls.__name__ == "GenericMeta":
                raise AttributeError
                # raise Exception(f'Cannot parse method {attr}')

            return cls.__dict__[attr]

    raise AttributeError


@node_visitor(ast.JoinedStr)
def _(node, ctx: Context):
    # TODO: Implement this properly
    return ir.ResExpr('')


def attr_shortcuts(cls, attr):
    if typeof(cls, ir.IntfType) and attr == 'dtype':
        return ir.ResExpr(cls.dtype)


@node_visitor(ast.Attribute)
def _(node, ctx: Context):
    value = visit_ast(node.value, ctx)
    if isinstance(value, ir.ResExpr):
        return ir.ResExpr(getattr(value.val, node.attr))

    if hasattr(value.dtype, node.attr):
        res = attr_shortcuts(value.dtype, node.attr)
        if res is not None:
            return res

        try:
            cls_attr = get_dict_attr(value.dtype, node.attr)

            # Maybe we have a class method, try to get function
            cls_attr = getattr(cls_attr, 'func', cls_attr)
        except AttributeError:
            # TODO: When is this necessary
            cls_attr = getattr(value.dtype, node.attr)

        # try:
        #     cls_attr = object.__getattribute__(value.dtype, node.attr).func
        # except Exception:
        #     cls_attr = getattr(value.dtype, node.attr)

        if isinstance(cls_attr, property):
            return resolve_func(cls_attr.fget, (value, ), {}, ctx)

        # TODO: What does this exactly do?
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


@node_visitor(ast.Dict)
def _(node, ctx: Context):
    return ir.ResExpr(py_eval_expr(node, ctx))


# TODO: Generalize for multiple loops withing list comprehension
@node_visitor(ast.ListComp)
def _(node, ctx: Context):
    if len(node.generators) != 1:
        raise SyntaxError(f'Only list comprehensions with a single for loop supported')

    iterator = visit_ast(node.generators[0].iter, ctx)
    target = visit_ast(node.generators[0].target, ctx)

    output_port_shadow_check(target.name, ctx)

    outter_var = None
    outter_namespace = None
    if target.name in ctx.scope:
        outter_var = ctx.scope[target.name]
        del ctx.scope[target.name]

    if target.name in ctx.local_namespace:
        outter_namespace = ctx.local_namespace[target.name]
        del ctx.local_namespace[target.name]

    stmts = []
    if isinstance(iterator, ir.ResExpr):
        vals = iterator.val
    elif isinstance(iterator, ir.CallExpr):
        if not const_func_args(iterator.args.values(), iterator.kwds):
            raise Exception(f'Generator needs to have constant arguments')

        args = tuple(node.val for node in iterator.args.values())
        vals = list(iterator.func(*args))
    else:
        vals = [ir.SubscriptExpr(iterator, ir.ResExpr(i)) for i in range(len(iterator.dtype))]

    for v in vals:
        ctx.local_namespace[target.name] = v
        res = visit_ast(node.elt, ctx)
        if isinstance(res, list):
            if len(res) > 1:
                raise SyntaxError(f'Complex expressions not supported for list comprehensions')

            res = res[0]

        stmts.append(res)

    del ctx.local_namespace[target.name]

    if outter_var:
        ctx.scope[target.name] = outter_var

    if outter_namespace:
        ctx.local_namespace[target.name] = outter_namespace

    return ir.ConcatExpr(stmts)


@node_visitor(ast.List)
def _(node: ast.List, ctx: Context):
    return ir.ResExpr(ir.ConcatExpr([visit_ast(e, ctx) for e in node.elts]))
