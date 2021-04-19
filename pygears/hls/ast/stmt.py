import ast
from . import Context, FuncContext, node_visitor, ir, visit_ast, GearContext
from pygears.core.gear import InSig, OutSig
from pygears.typing import is_type
from .cast import resolve_cast_func


def extend_stmts(stmts, extension):
    if extension:
        if not isinstance(extension, list):
            if isinstance(extension, ir.Statement):
                stmts.append(extension)
        else:
            for e in extension:
                if isinstance(e, ir.Statement):
                    stmts.append(e)


def output_port_shadow_check(name, ctx):
    if (isinstance(ctx, GearContext) and name in ctx.intfs and ctx.intfs[name].dtype.direction):
        raise SyntaxError(f'Variable "{name}" has the same name as the output'
                          f'interface. This is currently not supported')


def infer_targets(ctx, target, source):
    dtype = source.dtype
    if isinstance(target, ir.Name):
        ctx.alias_map[target.name] = source
        if target.name not in ctx.scope:
            var = ir.Variable(target.name, dtype, reg=target.name in ctx.registers)
            ctx.scope[target.name] = var
            target.obj = var
        else:
            output_port_shadow_check(target.name, ctx)

    elif isinstance(target, ir.ConcatExpr):
        # We can only make this check if the value is recognized PyGears type.
        # If it is some random Python type, just hope for the best
        if is_type(dtype) and len(dtype) != len(target.operands):
            raise SyntaxError(
                f'Cannot unpack value of type "{dtype!r}" with {len(dtype)} component(s) into {len(target.operands)} variables: '
                f'"{target}".')

        for i, t in enumerate(target.operands):
            infer_targets(ctx, t, ir.SubscriptExpr(source, ir.ResExpr(i)))
    elif isinstance(target, ir.SubscriptExpr):
        # # TODO: can we do some check here?
        if isinstance(target.val, ir.Name):
            ctx.alias_map[target.val.name] = ctx.ref(target.val.name)
    else:
        breakpoint()


def assign_targets(ctx: Context, target, source):
    infer_targets(ctx, target, source)

    if source.dtype in (OutSig, InSig):
        ctx.scope[target.name].val = source.val
        return None

    return ir.AssignValue(target, source)


@node_visitor(ast.AnnAssign)
def _(node, ctx: Context):
    targets = visit_ast(node.target, ctx)
    annotation = visit_ast(node.annotation, ctx)

    if not (isinstance(annotation, ir.ResExpr) or isinstance(annotation.val, type)
            or is_type(annotation.val)):
        raise SyntaxError(f'Variable annotation has to be a type, not "{annotation}"')

    if node.value is None:
        output_port_shadow_check(targets.name, ctx)
        ctx.scope[targets.name] = ir.Variable(targets.name, annotation.val)
        return

    if node.value:
        init = visit_ast(node.value, ctx)

        init_cast = ir.CastExpr(init, annotation.val)
        stmts = assign_targets(ctx, targets, init_cast)
        if not isinstance(stmts, list):
            stmts = [stmts]

        # for s in stmts:
        #     s.target.obj.val = s.val
        #     if init.val is None or getattr(init.val, 'unknown', False):
        #         s.target.obj.any_init = True

        return stmts


@node_visitor(ast.AugAssign)
def _(node, ctx: Context):
    target = visit_ast(node.target, ctx)
    value = visit_ast(node.value, ctx)

    # TODO: We should probably invoke truncate function to preserve the sign correctly
    return ir.AssignValue(
        target, ir.CastExpr(ir.BinOpExpr((ctx.ref(target.name), value), type(node.op)),
                            target.dtype))


@node_visitor(ast.Assign)
def _(node, ctx: Context):
    value = visit_ast(node.value, ctx)

    stmts = []
    for t in node.targets:
        targets = visit_ast(t, ctx)
        extend_stmts(stmts, assign_targets(ctx, targets, value))

    return stmts


@node_visitor(ast.Assert)
def _(node, ctx: Context):
    test = visit_ast(node.test, ctx)
    msg = node.msg.s if node.msg else 'Assertion failed.'
    return ir.Assert(test, msg=msg)


@node_visitor(ast.Break)
def _(node, ctx: Context):
    return ir.Jump('break')


@node_visitor(ast.Return)
def _(node: ast.Return, ctx: FuncContext):
    expr = visit_ast(node.value, ctx)

    if not isinstance(ctx, FuncContext):
        raise Exception('Return found outside function')

    # TODO: If there are multiple returns from a function, return types might
    # clash which is not supported right now. Check that this is not the case
    if ctx.ret_dtype is not None:
        expr = resolve_cast_func(expr, ctx.ret_dtype)
    else:
        ctx.ret_dtype = expr.dtype

    return ir.FuncReturn(ctx.funcref, expr)


@node_visitor(ast.Pass)
def _(node: ast.Pass, ctx: Context):
    return []


@node_visitor(ast.ImportFrom)
def _(node: ast.ImportFrom, ctx: Context):
    # TODO: Handle this properly
    return []
