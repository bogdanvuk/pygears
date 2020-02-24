import inspect
from . import Context, FuncContext, Function, Submodule, SyntaxError, node_visitor, nodes, visit_ast, visit_block
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
    if not all(isinstance(node, nodes.ResExpr) for node in kwds.values()):
        raise Exception("Not supproted")

    bind('gear/exec_context', 'compile')
    outputs = func(*local_in, **{k: v.val for k, v in kwds.items()})
    bind('gear/exec_context', 'hls')

    if isinstance(outputs, tuple):
        raise Exception("Not yet supported")

    gear_inst = outputs.producer.gear

    # def is_async_gen(func):
    #     return bool(func.__code__.co_flags & inspect.CO_ASYNC_GENERATOR)

    # if not is_async_gen(gear_inst.func):
    #     breakpoint()
    #     raise Exception("Not yet supported")

    in_ports = []
    for a, p in zip(args, gear_inst.in_ports):
        if isinstance(a, nodes.Interface):
            in_ports.append(a)
            continue

        intf_name = f'{gear_inst.basename}_{p.basename}'
        p.producer.source(HDLProducer())
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
        p.consumer.connect(HDLConsumer())
        out_ports.append(pydl_intf)

    stmts = []
    for a, intf in zip(args, in_ports):
        if a == intf:
            continue

        stmts.append(nodes.Assign(a, nodes.Name(intf.name, intf, ctx='store')))

    ctx.submodules.append(Submodule(gear_inst, in_ports, out_ports))

    return ctx.ref(out_ports[0].name), stmts
