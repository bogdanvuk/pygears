from pygears.conf import PluginBase, reg
from . import ir
from .ast.cast import resolve_cast_func
from .ast.call import resolve_gear_call, resolve_func
from pygears import Intf, reg

from pygears.core.gear import OutSig

from functools import reduce
from pygears.typing import Int, Uint, code, div, Queue, Integral, Float, Union, Bool, Maybe
from pygears.typing import is_type, typeof, Tuple, Array
from pygears.typing import floor, cast, signed, saturate
from pygears.typing.queue import QueueMeta

from pygears.util.utils import gather, qrange
from pygears.sim import clk
from pygears.lib.rng import qrange as qrange_gear
from pygears.lib.saturate import saturate as saturate_gear


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

    # TODO: Sort this casting out
    signed = typeof(op1.dtype, Int) or typeof(op2.dtype, Int)
    if signed and typeof(op1.dtype, Uint):
        op1_compare = resolve_cast_func(op1, Int)
    if signed and typeof(op2.dtype, Uint):
        op2_compare = resolve_cast_func(op2, Int)

    cond = ir.BinOpExpr((op1_compare, op2_compare), ir.opc.Gt)
    return ir.ConditionalExpr(cond=cond, operands=(op1, op2))


# TODO: Why do we need ir.TupleExpr?
def call_tuple(arg):
    if isinstance(arg, ir.ConcatExpr):
        return ir.TupleExpr(arg.operands)
    elif isinstance(arg, ir.TupleExpr):
        return arg
    elif isinstance(arg, ir.ResExpr):
        # TODO: Array is a list, so we have a workaround here
        if typeof(arg.dtype, (Tuple, Array, Queue)):
            return arg
        else:
            return ir.ResExpr(tuple(arg.val))
    elif typeof(arg.dtype, (Array, Tuple)):
        return ir.ConcatExpr([ir.SubscriptExpr(arg, ir.ResExpr(i)) for i in range(len(arg.dtype))])
    else:
        breakpoint()
        raise Exception

def call_tuple_add(op1, op2):
    if op1 == ir.ResExpr(()):
        return op2
    elif op2 == ir.ResExpr(()):
        return op1

    if not isinstance(op1, ir.ConcatExpr):
        op1 = call_tuple(op1)
    if not isinstance(op2, ir.ConcatExpr):
        op2 = call_tuple(op2)

    if isinstance(op1, ir.ConcatExpr):
        ops1 = op1.operands
    elif isinstance(op1, ir.ResExpr):
        ops1 = [ir.ResExpr(v) for v in op1.val]

    if isinstance(op2, ir.ConcatExpr):
        ops2 = op2.operands
    elif isinstance(op2, ir.ResExpr):
        ops2 = [ir.ResExpr(v) for v in op2.val]

    return ir.ConcatExpr(ops1 + ops2)


def call_len(arg, **kwds):
    if isinstance(arg, ir.ConcatExpr):
        return ir.ResExpr(len(arg.operands))

    if isinstance(arg, ir.ResExpr):
        return ir.ResExpr(len(arg.val))

    return ir.ResExpr(len(arg.dtype))


def call_print(*arg, **kwds):
    pass


def call_float(arg, **kwds):
    return ir.CastExpr(arg, cast_to=Float)


def call_int(arg, **kwds):
    # ignore cast
    if typeof(arg.dtype, (Uint, Int)):
        return arg
    elif typeof(arg.dtype, Integral):
        if arg.dtype.signed:
            return ir.CastExpr(arg, cast_to=Int[arg.dtype.width])
        else:
            return ir.CastExpr(arg, cast_to=Uint[arg.dtype.width])
    else:
        return ir.ResExpr(NotImplemented)


def call_all(arg, **kwds):
    return ir.ArrayOpExpr(arg, ir.opc.BitAnd)


def call_any(arg, **kwds):
    return ir.ArrayOpExpr(arg, ir.opc.BitOr)


# TODO: Can this be generalized a bit?
def call_max(*arg, **kwds):
    if len(arg) != 1:
        return reduce(max_expr, arg)

    arg = arg[0]

    assert typeof(arg.dtype, Tuple), 'Not supported yet...'

    op = []
    for field in arg.dtype.fields:
        op.append(ir.SubscriptExpr(arg, ir.ResExpr(field)))

    return reduce(max_expr, op)


def call_uint_matmul(obj, arg):
    return ir.CastExpr(ir.ConcatExpr(operands=[arg, obj]), cast_to=(obj.dtype @ arg.dtype))


def call_sub(obj, arg):
    return ir.CastExpr(arg, cast_to=obj.sub())


def outsig_write(obj, arg):
    return ir.AssignValue(obj, arg)


def call_get(obj, *args, **kwds):
    return obj


def call_get_nb(obj, *args, **kwds):
    return ir.AssignValue(ir.Component(obj, 'ready'), ir.res_true)
    # return obj


def call_pull_nb(obj):
    return ir.Component(obj, 'data')


def call_put_nb(obj, arg):
    ctx = reg['hls/ctx'][-1]

    if isinstance(obj, Intf):
        for p in ctx.gear.out_ports:
            if p.producer is obj:
                obj = ctx.ref(p.basename)
                break
        else:
            breakpoint()

    return [
        ir.Await('forward'),
        ir.AssignValue(ir.Component(obj, 'data'), arg),
        ir.AssignValue(ir.Component(obj, 'valid'), ir.res_true)
    ]
    # return obj


def call_clk(*arg, **kwds):
    return None


def call_empty(obj):
    return ir.UnaryOpExpr(ir.Component(obj, 'valid'), ir.opc.Not)


def call_ack(obj):
    return ir.AssignValue(ir.Component(obj, 'ready'), ir.res_true)


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


def call_isinstance(arg, dtype):
    if isinstance(dtype, ir.ResExpr):
        dtype = dtype.val

    if isinstance(arg, ir.ResExpr):
        return Bool(isinstance(arg.val, dtype))

    return ir.ResExpr(Bool(typeof(arg.dtype, dtype)))


def call_is_type(arg):
    if not isinstance(arg, ir.ResExpr):
        return ir.res_false

    return ir.ResExpr(Bool(is_type(arg.val)))


def call_typeof(arg, dtype):
    if isinstance(dtype, ir.ResExpr):
        dtype = dtype.val

    if not isinstance(arg, ir.ResExpr):
        return ir.res_false

    return ir.ResExpr(Bool(typeof(arg.val, dtype)))


# TODO: Implement sum and reduce
def call_sum(iterable, start):
    if not isinstance(iterable, ir.ConcatExpr):
        breakpoint()

    f = getattr(start.dtype, '__add__')
    ret = resolve_func(f, (start, iterable.operands[0]), {}, reg['hls/ctx'])

    if len(iterable.operands) == 1:
        return ret
    else:
        return call_sum(ir.ConcatExpr(iterable.operands[1:]), ret)


def call_subs_fix_index(orig, path, val):
    parts = []
    for i in range(len(orig.dtype)):
        p = ir.SubscriptExpr(orig, ir.ResExpr(i))
        if isinstance(path, tuple):
            if path[0].val == i:
                p = ir.CastExpr(call_subs(p, path[1:], val), p.dtype)
        elif path.val == i:
            p = ir.CastExpr(val, p.dtype)

        parts.append(p)

    return ir.CastExpr(ir.ConcatExpr(parts), orig.dtype)


def call_subs_var_index(orig, path, val):
    parts = []
    for i in range(len(orig.dtype)):
        p = ir.SubscriptExpr(orig, ir.ResExpr(i))
        if isinstance(path, tuple):
            cond = ir.BinOpExpr((path[0], ir.ResExpr(i)), ir.opc.Eq)
            repl = ir.CastExpr(call_subs(p, path[1:], val), p.dtype)
        else:
            cond = ir.BinOpExpr((path, ir.ResExpr(i)), ir.opc.Eq)
            repl = ir.CastExpr(val, p.dtype)

        parts.append(ir.ConditionalExpr((repl, p), cond))

    return ir.CastExpr(ir.ConcatExpr(parts), orig.dtype)


def call_subs(orig, *args, **kwds):
    if args:
        path, val = args
        if isinstance(path, tuple) and len(path) == 1:
            path = path[0]

        if isinstance(path, tuple) and isinstance(path[0], ir.ResExpr):
            return call_subs_fix_index(orig, path, val)
        elif not isinstance(path, tuple) and isinstance(path, ir.ResExpr):
            return call_subs_fix_index(orig, path, val)
        else:
            return call_subs_var_index(orig, path, val)

    if kwds:
        parts = []
        for i, name in enumerate(orig.dtype.fields):
            p = ir.SubscriptExpr(orig, ir.ResExpr(i))
            if name in kwds:
                p = ir.CastExpr(kwds[name], p.dtype)

            parts.append(p)

        return ir.CastExpr(ir.ConcatExpr(parts), orig.dtype)

def call_maybe_get(arg):
    return ir.CastExpr(ir.SubscriptExpr(arg, ir.ResExpr(0)), cast_to=arg.dtype.dtype)


def call_maybe_some(arg, val):
    if isinstance(arg, ir.ResExpr):
        breakpoint()
        arg = arg.dtype

    return ir.CastExpr(ir.ConcatExpr([val, ir.ResExpr(1)]), cast_to=arg)


def call_enumerate(arg):
    arg.enumerated = True
    return arg


def call_qrange(*args):
    return resolve_gear_call(qrange_gear.func, args, {})


def call_range(*args):
    ret = ir.CallExpr(range,
                      dict(zip(['start', 'stop', 'step'], args)),
                      params={'return': Queue[args[0].dtype]})

    ret.pass_eot = False
    return ret


def call_breakpoint():
    return None


def ir_builtin(func):
    reg['hls/ir_builtins'].get(func, None)


class AddIntfOperPlugin(PluginBase):
    @classmethod
    def bind(cls):
        ir_builtins = {
            gather: call_gather,
            all: call_all,
            any: call_any,
            max: call_max,
            clk: call_clk,
            float: call_float,
            int: call_int,
            len: call_len,
            print: call_print,
            type: call_type,
            isinstance: call_isinstance,
            tuple: call_tuple,
            tuple.__add__: call_tuple_add,
            sum: call_sum,
            is_type: call_is_type,
            typeof: call_typeof,
            div: call_div,
            ir.IntfType.empty: call_empty,
            ir.IntfType.ack: call_ack,
            Intf.get: call_get,
            Intf.get_nb: call_get_nb,
            Intf.put_nb: call_put_nb,
            ir.IntfType.pull_nb: call_pull_nb,
            cast: call_cast,
            signed: call_signed,
            QueueMeta.sub: call_sub,
            Maybe.get: call_maybe_get,
            Maybe.some: call_maybe_some,
            Maybe.some.__func__: call_maybe_some, # TODO: Why do we need both this and above
            object.__getattribute__(Array, 'subs').func: call_subs,
            object.__getattribute__(Tuple, 'subs').func: call_subs,
            object.__getattribute__(Uint, '__matmul__'): call_uint_matmul,
            OutSig.write: outsig_write,
            Array.code: call_code,
            Tuple.code: call_code,
            code: call_code,
            qrange: call_qrange,
            range: call_range,
            enumerate: call_enumerate
        }

        import sys
        if sys.version_info[1] >= 7:
            ir_builtins[breakpoint] = call_breakpoint

        int_unops = {
            ir.opc.Invert: '__invert__',
            ir.opc.UAdd: '__pos__',
            ir.opc.USub: '__neg__',
        }

        # TODO: User @wraps for better error reporting
        for op, name in int_unops.items():
            ir_builtins[getattr(int, name)] = lambda a, *, x=op: ir.UnaryOpExpr(call_int(a), x)

        int_binops = {
            ir.opc.Add: '__add__',
            ir.opc.BitAnd: '__and__',
            ir.opc.BitOr: '__or__',
            ir.opc.BitXor: '__xor__',
            ir.opc.Div: '__truediv__',
            ir.opc.Eq: '__eq__',
            ir.opc.Gt: '__gt__',
            ir.opc.GtE: '__ge__',
            ir.opc.FloorDiv: '__floordiv__',
            ir.opc.Lt: '__lt__',
            ir.opc.LtE: '__le__',
            ir.opc.LShift: '__lshift__',
            ir.opc.Mod: '__mod__',
            ir.opc.Mult: '__mul__',
            ir.opc.NotEq: '__ne__',
            ir.opc.RShift: '__rshift__',
            ir.opc.Sub: '__sub__'
        }

        # TODO: User @wraps for better error reporting
        for op, name in int_binops.items():
            ir_builtins[getattr(int, name)] = lambda a, b, *, x=op: ir.BinOpExpr(
                (call_int(a), b), x)

        int_binrops = {
            ir.opc.Add: '__radd__',
            ir.opc.BitAnd: '__rand__',
            ir.opc.BitOr: '__ror__',
            ir.opc.BitXor: '__rxor__',
            ir.opc.Div: '__rtruediv__',
            ir.opc.FloorDiv: '__rfloordiv__',
            ir.opc.LShift: '__rlshift__',
            ir.opc.Mod: '__rmod__',
            ir.opc.Mult: '__rmul__',
            ir.opc.RShift: '__rshift__',
            ir.opc.Sub: '__rsub__'
        }

        # TODO: User @wraps for better error reporting
        for op, name in int_binrops.items():
            # TODO: Test NotImplemented part
            def intop(a, b, *, x=op):
                a_conv = call_int(a)
                if a_conv == ir.ResExpr(NotImplemented):
                    return ir.ResExpr(NotImplemented)

                return ir.BinOpExpr((a_conv, b), x)

            ir_builtins[getattr(int, name)] = intop

        reg['hls/ir_builtins'] = ir_builtins
