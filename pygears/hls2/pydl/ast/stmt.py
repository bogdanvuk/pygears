import ast
from . import Context, FuncContext, SyntaxError, node_visitor, nodes, visit_ast
from .utils import add_to_list
from .cast import resolve_cast_func


class UnknownName(SyntaxError):
    pass


def assign_targets(ctx, target, source, obj_factory=None):
    if isinstance(target, nodes.ConcatExpr):
        stmts = []
        for i, op in enumerate(target.operands):
            add_to_list(
                stmts,
                assign_targets(ctx, op,
                               nodes.SubscriptExpr(source, nodes.ResExpr(i)),
                               obj_factory))
        return stmts

    if isinstance(target, nodes.SubscriptExpr):
        return nodes.Assign(source, target)

    if target.name not in ctx.scope:
        if obj_factory is None:
            breakpoint()
            raise NameError

        var = obj_factory(target.name, source.dtype)
        ctx.scope[target.name] = var
        target = nodes.Name(target.name, var, target.ctx)

    return nodes.Assign(source, target)


@node_visitor(ast.AnnAssign)
def _(node, ctx: Context):
    targets = visit_ast(node.target, ctx)
    annotation = visit_ast(node.annotation, ctx)

    if node.value is None:
        ctx.scope[targets.name] = nodes.Variable(targets.name, annotation.val)
        return

    if node.value:
        init = visit_ast(node.value, ctx)

        init_cast = nodes.ResExpr(annotation.val(init.val))
        stmts = assign_targets(ctx, targets, init_cast, nodes.Register)
        if not isinstance(stmts, list):
            stmts = [stmts]

        for s in stmts:
            s.var.obj.val = s.expr
            if init.val is None:
                s.var.obj.any_init = True


@node_visitor(ast.AugAssign)
def _(node, ctx: Context):
    target = visit_ast(node.target, ctx)
    value = visit_ast(node.value, ctx)
    return nodes.Assign(
        nodes.BinOpExpr((ctx.ref(target.name), value), type(node.op)), target)


@node_visitor(ast.Assign)
def _(node, ctx: Context):
    value = visit_ast(node.value, ctx)
    stmts = []
    for t in node.targets:
        targets = visit_ast(t, ctx)
        add_to_list(stmts, assign_targets(ctx, targets, value))

    return stmts


@node_visitor(ast.Assert)
def _(node, ctx: Context):
    test = visit_ast(node.test, ctx)
    msg = node.msg.s if node.msg else 'Assertion failed.'
    return nodes.Assert(test, msg=msg)


@node_visitor(ast.Return)
def _(node: ast.Return, ctx: FuncContext):
    expr = visit_ast(node.value, ctx)

    if not isinstance(ctx, FuncContext):
        raise Exception('Return found outside function')

    if ctx.ret_dtype is not None:
        expr = resolve_cast_func(expr, ctx.ret_dtype)
    else:
        ctx.ret_dtype = expr.dtype

    return nodes.Return(expr)
