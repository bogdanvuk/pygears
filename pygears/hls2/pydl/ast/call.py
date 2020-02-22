import ast
import typing
import inspect
from . import Submodule, Context, FuncContext, SyntaxError, node_visitor, nodes, visit_ast, visit_block, Function
from .inline import form_gear_args, call_gear
from .builtins import builtins
from .cast import resolve_cast_func
from pygears import Intf, registry
from pygears.core.partial import extract_arg_kwds, combine_arg_kwds, Partial
from pygears.typing import is_type, typeof, Tuple, Array


def parse_func_args(args, kwds, ctx):
    if args is None:
        args = []

    if kwds is None:
        kwds = []

    func_args = []
    for arg in args:
        if isinstance(arg, ast.Starred):
            var = visit_ast(arg.value, ctx)

            # if not isinstance(var, nodes.ConcatExpr):
            #     raise VisitError(f'Cannot unpack variable "{arg.value.id}"')

            # if not typeof(var.dtype, (Tuple, Array)):
            #     breakpoint()
            #     raise Exception('Unsupported')

            if isinstance(var, nodes.ResExpr) and isinstance(var.val, list):
                func_args.extend(var.val)
            else:
                for i in range(len(var.dtype)):
                    func_args.append(
                        nodes.SubscriptExpr(val=var, index=nodes.ResExpr(i)))

        else:
            func_args.append(visit_ast(arg, ctx))

    func_kwds = {kwd.arg: visit_ast(kwd.value, ctx) for kwd in kwds}

    return func_args, func_kwds


@node_visitor(ast.Call)
def _(node, ctx: Context):
    name = visit_ast(node.func, ctx)

    assert isinstance(name, nodes.ResExpr)

    func = name.val

    args, kwds = parse_func_args(node.args, node.keywords, ctx)

    if (func in builtins) and (isinstance(builtins[func], Partial)):
        return call_gear(builtins[func], *form_gear_args(args, kwds, func), ctx)

    if isinstance(func, Partial):
        return call_gear(func, *form_gear_args(args, kwds, func), ctx)

    if func in builtins:
        return builtins[func](*args, **kwds)

    # If all arguments are resolved expressions, maybe we can evaluate the
    # function at compile time
    if (all(isinstance(node, nodes.ResExpr) for node in args)
            and all(isinstance(node, nodes.ResExpr)
                    for node in kwds.values())):
        return nodes.ResExpr(
            func(*(a.val for a in args), **{n: v.val
                                            for n, v in kwds.items()}))

    # If we are dealing with bound methods
    if not inspect.isbuiltin(func) and hasattr(func, '__self__'):
        raise Exception

    if is_type(func):
        return resolve_cast_func(args[0], func)
    else:
        return parse_func_call(func, args, kwds, ctx)

    if isinstance(func, nodes.Expr):
        return func


def parse_func_call(func: typing.Callable, args, kwds, ctx: Context):
    funcref = Function(func, args, kwds, uniqueid=len(ctx.functions))
    if not funcref in ctx.functions:
        func_ctx = FuncContext(funcref, args, kwds)
        registry('hls/ctx').append(func_ctx)
        pydl_ast = visit_ast(funcref.ast, func_ctx)
        registry('hls/ctx').pop()
        ctx.functions[funcref] = (pydl_ast, func_ctx)
    else:
        (pydl_ast, func_ctx) = ctx.functions[funcref]

    return nodes.FunctionCall(operands=list(func_ctx.args.values()),
                              ret_dtype=func_ctx.ret_dtype,
                              name=funcref.name)
