import ast
import typing
import inspect
from . import Context, FuncContext, Function, node_visitor, ir, visit_ast
from .inline import form_gear_args, call_gear
from .cast import resolve_cast_func
from pygears import Intf, registry
from pygears.core.partial import Partial
from functools import reduce
from pygears.typing import Int, Uint, code, div
from pygears.typing import is_type, typeof, Tuple, Array
from pygears.typing import floor, cast, signed
from pygears.typing.queue import QueueMeta

from pygears.util.utils import gather, qrange
from pygears.sim import clk
from pygears.core.gear import OutSig
from pygears.lib.rng import qrange as qrange_gear

from pygears.core.gear_inst import gear_signature, infer_params, get_function_context_dict, TypeMatchError, TooManyArguments, GearArgsNotSpecified


def parse_func_args(args, kwds, ctx):
    if args is None:
        args = []

    if kwds is None:
        kwds = []

    func_args = []
    for arg in args:
        if isinstance(arg, ast.Starred):
            var = visit_ast(arg.value, ctx)

            if isinstance(var, ir.ResExpr) and isinstance(var.val, list):
                func_args.extend(var.val)
            else:
                for i in range(len(var.dtype)):
                    func_args.append(
                        ir.SubscriptExpr(val=var, index=ir.ResExpr(i)))

        else:
            func_args.append(visit_ast(arg, ctx))

    func_kwds = {kwd.arg: visit_ast(kwd.value, ctx) for kwd in kwds}

    return func_args, func_kwds


def get_gear_signatures(func, args, kwds):
    alternatives = [func] + getattr(func, 'alternatives', [])

    signatures = []

    for f in alternatives:
        meta_kwds = f.__globals__['meta_kwds']
        try:
            args_dict, templates = gear_signature(f, args, kwds, meta_kwds)
        except (TooManyArguments, GearArgsNotSpecified):
            pass
        else:
            signatures.append((f, args_dict, templates))

    return signatures


def const_func_args(args, kwds):
    return (all(isinstance(node, ir.ResExpr) for node in args)
            and all(isinstance(node, ir.ResExpr) for node in kwds.values()))


def resolve_compile_time(func, args, kwds):
    # If all arguments are resolved expressions, maybe we can evaluate the
    # function at compile time
    return ir.ResExpr(
        func(*(a.val for a in args), **{n: v.val
                                        for n, v in kwds.items()}))


def resolve_gear_cal(func, args, kwds):
    args, kwds = form_gear_args(args, kwds, func)

    for f, args, templates in get_gear_signatures(func, args, kwds):
        try:
            params = infer_params(args, templates,
                                  get_function_context_dict(f))
        except TypeMatchError:
            pass
        else:
            return ir.GenCallExpr(f, args, kwds, params)


def call_floor(arg):
    t_arg = arg.dtype
    int_cls = Int if t_arg.signed else Uint
    arg_to_int = ir.CastExpr(arg, int_cls[t_arg.width])
    if t_arg.fract >= 0:
        return ir.BinOpExpr((arg_to_int, ir.ResExpr(Uint(t_arg.fract))),
                               ir.opc.RShift)
    else:
        return ir.BinOpExpr((arg_to_int, ir.ResExpr(Uint(-t_arg.fract))),
                               ir.opc.LShift)


def call_div(a, b, subprec):
    t_a = a.dtype
    t_b = b.dtype

    t_div = div(t_a, t_b, int(subprec.val))

    def fixp__div__(op1: t_a, op2: t_b) -> t_div:
        return t_div(op1) // op2

    return fixp__div__


def max_expr(op1, op2):
    op1_compare = op1
    op2_compare = op2

    #TODO: Sort this casting out
    signed = typeof(op1.dtype, Int) or typeof(op2.dtype, Int)
    if signed and typeof(op1.dtype, Uint):
        op1_compare = resolve_cast_func(op1, Int)
    if signed and typeof(op2.dtype, Uint):
        op2_compare = resolve_cast_func(op2, Int)

    cond = ir.BinOpExpr((op1_compare, op2_compare), ir.opc.Gt)
    return ir.ConditionalExpr(cond=cond, operands=(op1, op2))


def call_len(arg, **kwds):
    return ir.ResExpr(len(arg.val))


def call_print(*arg, **kwds):
    pass


def call_int(arg, **kwds):
    # ignore cast
    if typeof(arg.dtype, (Uint, Int)):
        return arg
    else:
        return ir.CastExpr(arg, cast_to=Uint[len(arg.dtype)])


def call_all(arg, **kwds):
    return ir.ArrayOpExpr(arg, ir.opc.BitAnd)


def call_max(*arg, **kwds):
    if len(arg) != 1:
        return reduce(max_expr, arg)

    arg = arg[0]

    assert typeof(arg.dtype, Tuple), 'Not supported yet...'

    op = []
    for field in arg.dtype.fields:
        op.append(ir.SubscriptExpr(arg, ir.ResExpr(field)))

    return reduce(max_expr, op)


def call_sub(obj, arg):
    return ir.CastExpr(arg, cast_to=obj.sub())


def outsig_write(obj, arg):
    return ir.SignalStmt(ir.SignalDef(obj), arg)


def call_get(obj, *args, **kwds):
    return obj


def call_get_nb(obj, *args, **kwds):
    return obj


def call_clk(*arg, **kwds):
    return None


def call_empty(obj, *arg, **kwds):
    assert not arg, 'Empty should be called without arguments'
    expr = ir.IntfDef(intf=obj.intf, _name=obj.name, context='valid')
    return ir.UnaryOpExpr(expr, ir.opc.Not)


def call_gather(*arg, **kwds):
    return ir.ConcatExpr(operands=list(arg))


def call_cast(arg, cast_type):
    return resolve_cast_func(arg, cast_type.val)


def call_signed(val):
    if val.dtype.signed:
        return val

    if typeof(val.dtype, Uint):
        return resolve_cast_func(val, Int)

    raise Exception("Unsupported signed cast")


def call_code(val, cast_type=ir.ResExpr(Uint)):
    cast_type = code(val.dtype, cast_type.val)
    if val.dtype == cast_type:
        return val

    return ir.CastExpr(val, cast_to=cast_type)


def call_type(arg):
    return ir.ResExpr(arg.dtype)


def call_enumerate(arg):
    arg.enumerated = True
    return arg


def call_qrange(*args):
    return resolve_gear_cal(qrange_gear.func, args, {})


def call_range(*args):
    ret = resolve_gear_cal(qrange_gear.func, args, {})
    ret.pass_eot = False
    return ret


def call_breakpoint():
    return None


builtins = {
    gather: call_gather,
    all: call_all,
    max: call_max,
    clk: call_clk,
    int: call_int,
    len: call_len,
    print: call_print,
    type: call_type,
    div: call_div,
    floor: call_floor,
    Intf.empty: call_empty,
    Intf.get: call_get,
    Intf.get_nb: call_get_nb,
    cast: call_cast,
    signed: call_signed,
    QueueMeta.sub: call_sub,
    OutSig.write: outsig_write,
    Array.code: call_code,
    Tuple.code: call_code,
    code: call_code,
    qrange: call_qrange,
    range: call_range,
    enumerate: call_enumerate,
    breakpoint: call_breakpoint
}

compile_time_builtins = {
    all, max, int, len, type, div, floor, cast, QueueMeta.sub, Array.code,
    Tuple.code, code
}


@node_visitor(ast.Call)
def _(node, ctx: Context):
    name = visit_ast(node.func, ctx)

    assert isinstance(name, ir.ResExpr)

    func = name.val

    args, kwds = parse_func_args(node.args, node.keywords, ctx)

    if is_type(func):
        if const_func_args(args, kwds):
            return resolve_compile_time(func, args, kwds)

        return resolve_cast_func(args[0], func)

    # If we are dealing with bound methods
    if not inspect.isbuiltin(func) and hasattr(func, '__self__'):
        raise Exception

    if isinstance(func, Partial):
        intf, stmts = call_gear(func, *form_gear_args(args, kwds, func), ctx)
        ctx.pydl_parent_block.stmts.extend(stmts)
        return intf

    if func in compile_time_builtins and const_func_args(args, kwds):
        return resolve_compile_time(func, args, kwds)

    if func in builtins:
        return builtins[func](*args, **kwds)

    if const_func_args(args, kwds):
        return resolve_compile_time(func, args, kwds)
    else:
        return parse_func_call(func, args, kwds, ctx)


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

    return ir.FunctionCall(operands=list(func_ctx.args.values()),
                              ret_dtype=func_ctx.ret_dtype,
                              name=funcref.name)
