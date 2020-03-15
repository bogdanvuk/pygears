import inspect
from . import Context, FuncContext, Function, Submodule, SyntaxError, node_visitor, ir, visit_ast, visit_block
from pygears import Intf, bind
from pygears.core.partial import combine_arg_kwds, extract_arg_kwds
from pygears.core.port import InPort, HDLConsumer, HDLProducer


def form_gear_args(args, kwds, func):
    kwd_args, kwds_only = extract_arg_kwds(kwds, func)
    args_only = combine_arg_kwds(args, kwd_args, func)

    return args_only, kwds_only


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
