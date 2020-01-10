import ast
import inspect
from . import Submodule, Context, SyntaxError, node_visitor, nodes, visit_ast, visit_block
from ..pydl_builtins import builtins
from pygears import Intf, registry
from pygears.core.partial import extract_arg_kwds, combine_arg_kwds, Partial
from pygears.typing import is_type


def parse_func_args(args, kwds, ctx):
    if args is None:
        args = []

    if kwds is None:
        kwds = []

    arg_unpacked = []
    for arg in args:
        if isinstance(arg, ast.Starred):
            breakpoint()
            # var = get_context_var(arg.value.id, ctx)

            # if not isinstance(var, ConcatExpr):
            #     raise VisitError(f'Cannot unpack variable "{arg.value.id}"')

            # for i in range(len(var.operands)):
            #     arg_unpacked.append(
            #         ast.fix_missing_locations(
            #             ast.Subscript(value=arg.value,
            #                           slice=ast.Index(value=ast.Num(i)),
            #                           ctx=ast.Load)))
        else:
            arg_unpacked.append(arg)

    func_args = [visit_ast(arg, ctx) for arg in arg_unpacked]

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
        ctx.pydl_parent_block.stmts.append(nodes.Assign(ctx.ref(intf.name, ctx='store'), a))

    ctx.submodules.append(Submodule(gear_inst, in_ports, out_ports))

    return ctx.ref(out_ports[0].name)


@node_visitor(ast.Call)
def _(node, ctx: Context):
    name = visit_ast(node.func, ctx)

    assert isinstance(name, nodes.ResExpr)

    func = name.val

    args, kwds = parse_func_args(node.args, node.keywords, ctx)

    kwd_args, kwds_only = extract_arg_kwds(kwds, func)
    args_only = combine_arg_kwds(args, kwd_args, func)

    if isinstance(func, Partial):
        return cal_gear(func, args_only, kwds_only, ctx)

    # If all arguments are resolved expressions, maybe we can evaluate the
    # function at compile time
    if (all(isinstance(node, nodes.ResExpr) for node in args_only) and all(
            isinstance(node, nodes.ResExpr) for node in kwds_only.values())):
        return nodes.ResExpr(
            func(*(a.val for a in args_only),
                 **{n: v.val
                    for n, v in kwds_only.items()}))

    # If we are dealing with bound methods
    if not inspect.isbuiltin(func) and hasattr(func, '__self__'):
        raise Exception

    if func in builtins:
        func = builtins[func](*args_only, **kwds_only)
    elif is_type(func):
        raise Exception
        # from .hdl_cast import resolve_cast_func
        # func = resolve_cast_func(func_args[0], func)

    if isinstance(func, nodes.Expr):
        return func
