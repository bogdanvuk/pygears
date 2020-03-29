import inspect
import typing
from . import Context, FuncContext, Function, Submodule, SyntaxError, node_visitor, ir, visit_ast, visit_block
from pygears import Intf, bind, registry
from pygears.core.partial import combine_arg_kwds, extract_arg_kwds
from pygears.core.port import InPort, HDLConsumer, HDLProducer
from pygears.core.datagear import is_datagear, get_datagear_func
from pygears.core.gear import gear_explicit_params


def form_gear_args(args, kwds, func):
    kwd_args, kwds_only = extract_arg_kwds(kwds, func)
    args_only = combine_arg_kwds(args, kwd_args, func)

    return args_only, kwds_only


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

    return ir.FunctionCall(
        operands=list(func_ctx.args.values()),
        ret_dtype=func_ctx.ret_dtype,
        name=funcref.name)


def call_datagear(func, args, params, ctx: Context):
    f = get_datagear_func(func)
    kwds = gear_explicit_params(f, params)
    kwds = {n: ir.ResExpr(v) for n, v in kwds.items()}
    return parse_func_call(f, args, kwds, ctx)


def call_gear(func, args, kwds, ctx: Context):
    local_in = []
    for i, a in enumerate(args):
        intf = Intf(a.dtype)
        intf.source(HDLProducer())
        local_in.append(intf)

    # local_in = [Intf(a.dtype) for a in args]
    if not all(isinstance(node, ir.ResExpr) for node in kwds.values()):
        raise Exception("Not supproted")

    bind('gear/exec_context', 'compile')
    outputs = func(*local_in, **{k: v.val for k, v in kwds.items()})
    bind('gear/exec_context', 'hls')

    if isinstance(outputs, tuple):
        gear_inst = outputs[0].producer.gear
    else:
        gear_inst = outputs.producer.gear

    in_ports = []
    for a, p in zip(args, gear_inst.in_ports):
        if isinstance(a, ir.Interface):
            in_ports.append(a)
            continue

        intf_name = f'{gear_inst.basename}_{p.basename}'
        p.producer.source(HDLProducer())
        pydl_intf = ir.Variable(intf_name, val=p.producer)
        ctx.scope[intf_name] = pydl_intf
        in_ports.append(pydl_intf)

    out_ports = []
    for p in gear_inst.out_ports:
        intf_name = f'{gear_inst.basename}_{p.basename}'
        pydl_intf = ir.Variable(intf_name, val=p.consumer)
        ctx.scope[intf_name] = pydl_intf
        p.consumer.connect(HDLConsumer())
        out_ports.append(pydl_intf)

    stmts = []
    for a, intf in zip(args, in_ports):
        if a == intf:
            continue

        stmts.append(ir.AssignValue(ir.Name(intf.name, intf, ctx='store'), a))

    ctx.submodules.append(Submodule(gear_inst, in_ports, out_ports))

    if len(out_ports) == 1:
        return ctx.ref(out_ports[0].name), stmts
    else:
        return ir.TupleExpr(tuple(ctx.ref(p.name) for p in out_ports)), stmts
