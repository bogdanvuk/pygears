import ast
from . import Context, SyntaxError, node_visitor, nodes, visit_ast, visit_block
from ..pydl_arith import resolve_arith_func
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

    if all(isinstance(v, nodes.ResExpr) for v in res.values()):
        return res['body'].val if res['test'].val else res['orelse']

    return nodes.ConditionalExpr(operands=(res['body'], res['orelse']),
                                 cond=res['test'])


@node_visitor(ast.Num)
def num(node, ctx: Context):
    return nodes.ResExpr(cast(node.n, Integer))


@node_visitor(ast.Name)
def name(node, ctx: Context):
    if isinstance(node.ctx, ast.Load):
        if node.id not in ctx.scope:
            if node.id in ctx.local_namespace:
                return nodes.ResExpr(ctx.local_namespace[node.id])

            if node.id in ctx.local_namespace['__builtins__']:
                return nodes.ResExpr(ctx.local_namespace['__builtins__'][node.id])

            raise SyntaxError(f"Name '{node.id}' not found", node.lineno)

        if isinstance(ctx.scope[node.id], nodes.ResExpr):
            return ctx.scope[node.id]

        return ctx.ref(node.id, ctx='load')

    if isinstance(node.ctx, ast.Store):
        if node.id in ctx.scope:
            return ctx.ref(node.id, ctx='store')

        return nodes.Name(node.id, None, 'store')


@node_visitor(ast.UnaryOp)
def parse_unaryop(node, ctx: Context):
    operand = visit_ast(node.operand, ctx)
    if operand is None:
        return None

    if isinstance(operand, nodes.ResExpr):
        return eval(
            compile(ast.Expression(
                ast.fix_missing_locations(type(node.op)(ast.Name('var')))),
                    filename="<ast>",
                    mode="eval"), {'var': operand.val}, globals())

    operator = nodes.OPMAP[type(node.op)]

    if operator == '!':
        return nodes.create_oposite(operand)

    return nodes.UnaryOpExpr(operand, operator)


@node_visitor(ast.Tuple)
def _(node, ctx: Context):
    return nodes.ConcatExpr([visit_ast(item, ctx) for item in node.elts])


@node_visitor(ast.Subscript)
def _(node, ctx: Context):
    return nodes.SubscriptExpr(visit_ast(node.value, ctx),
                               visit_ast(node.slice, ctx))


def visit_bin_expr(op, operands, ctx: Context):
    res = resolve_arith_func(op, tuple(visit_ast(p, ctx) for p in operands), ctx)
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
    if isinstance(value, nodes.Name) and isinstance(value.obj,
                                                    nodes.Interface):
        return nodes.ResExpr(value.obj.intf.dtype)

    return nodes.AttrExpr(value, node.attr)


@node_visitor(ast.Str)
def _(node, ctx: Context):
    return nodes.ResExpr(node.s)


@node_visitor(ast.NameConstant)
def _(node, ctx: Context):
    return nodes.ResExpr(node.value)


@node_visitor(ast.Index)
def _(node, ctx: Context):
    return visit_ast(node.value, ctx)


@node_visitor(ast.Assert)
def parse_assert(node, module_data):
    test = visit_ast(node.test, module_data)
    msg = node.msg.s if node.msg else 'Assertion failed.'
    return nodes.AssertExpr(test=test, msg=msg)
