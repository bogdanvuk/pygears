import ast
import typing
import inspect
from . import Submodule, Context, FuncContext, SyntaxError, node_visitor, nodes, visit_ast, visit_block, Function
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

            for i in range(len(var.dtype)):
                func_args.append(
                    nodes.SubscriptExpr(val=var, index=nodes.ResExpr(i)))

        else:
            func_args.append(visit_ast(arg, ctx))

    func_kwds = {kwd.arg: visit_ast(kwd.value, ctx) for kwd in kwds}

    return func_args, func_kwds


def cal_gear(func, args, kwds, ctx: Context):
    local_in = [Intf(a.dtype) for a in args]
    if not all(isinstance(node, nodes.ResExpr) for node in kwds.values()):
        raise Exception("Not supproted")

    outputs = func(*local_in, **{k: v.val for k, v in kwds.items()})

    if isinstance(outputs, tuple):
        raise Exception("Not yet supported")

    gear_inst = outputs.producer.gear

    def is_async_gen(func):
        return bool(func.__code__.co_flags & inspect.CO_ASYNC_GENERATOR)

    if not is_async_gen(gear_inst.func):
        raise Exception("Not yet supported")

    in_ports = []
    for a, p in zip(args, gear_inst.in_ports):
        if isinstance(a, nodes.Interface):
            in_ports.append(a)
            continue

        intf_name = f'{gear_inst.basename}_{p.basename}'
        pydl_intf = nodes.Interface(p.producer, 'out', intf_name)
        ctx.scope[intf_name] = pydl_intf
        in_ports.append(pydl_intf)

    if len(gear_inst.out_ports) != 1:
        raise Exception("Not supported")

    out_ports = []
    for p in gear_inst.out_ports:
        intf_name = f'{gear_inst.basename}_{p.basename}'
        pydl_intf = nodes.Interface(p.consumer, 'in', intf_name)
        ctx.scope[intf_name] = pydl_intf
        out_ports.append(pydl_intf)

    for a, intf in zip(args, in_ports):
        ctx.pydl_parent_block.stmts.append(
            nodes.Assign(a, ctx.ref(intf.name, ctx='store')))

    ctx.submodules.append(Submodule(gear_inst, in_ports, out_ports))

    return ctx.ref(out_ports[0].name)


def form_gear_args(args, kwds, func):
    kwd_args, kwds_only = extract_arg_kwds(kwds, func)
    args_only = combine_arg_kwds(args, kwd_args, func)

    return args_only, kwds_only


@node_visitor(ast.Call)
def _(node, ctx: Context):
    name = visit_ast(node.func, ctx)

    assert isinstance(name, nodes.ResExpr)

    func = name.val

    args, kwds = parse_func_args(node.args, node.keywords, ctx)

    if (func in builtins) and (isinstance(builtins[func], Partial)):
        return cal_gear(builtins[func], *form_gear_args(args, kwds, func), ctx)

    if isinstance(func, Partial):
        return cal_gear(func, *form_gear_args(args, kwds, func), ctx)

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

    if func in builtins:
        return builtins[func](*args, **kwds)
    elif is_type(func):
        return resolve_cast_func(args[0], func)
    else:
        return parse_func_call(func, args, kwds, ctx)

    if isinstance(func, nodes.Expr):
        return func


def parse_func_call(func: typing.Callable, args, kwds, ctx: Context):
    funcref = Function(func, args, kwds, uniqueid=len(ctx.functions))
    if not funcref in ctx.functions:
        func_ctx = FuncContext(funcref, args, kwds)
        pydl_ast = visit_ast(funcref.ast, func_ctx)
        ctx.functions[funcref] = (pydl_ast, func_ctx)
    else:
        (pydl_ast, func_ctx) = ctx.functions[funcref]

    return nodes.FunctionCall(operands=list(func_ctx.args.values()),
                              ret_dtype=func_ctx.ret_dtype,
                              name=funcref.name)
