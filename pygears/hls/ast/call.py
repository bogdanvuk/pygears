import ast
import sys
import typing
import inspect
import weakref
from functools import partial
from . import Context, FuncContext, Function, node_visitor, ir, visit_ast
from .inline import form_gear_args, call_gear, parse_func_call
from .cast import resolve_cast_func
from pygears import Intf, registry

from pygears.core.partial import Partial, MultiAlternativeError
from pygears.core.gear import OutSig, gear_explicit_params

from functools import reduce
from pygears.typing import Int, Uint, code, div, Queue, Integral
from pygears.typing import is_type, typeof, Tuple, Array
from pygears.typing import floor, cast, signed, saturate
from pygears.typing.queue import QueueMeta

from pygears.util.utils import gather, qrange
from pygears.sim import clk
from pygears.lib.rng import qrange as qrange_gear
from pygears.lib.saturate import saturate as saturate_gear

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
    kwds = {
        n: v.val if isinstance(v, ir.ResExpr) else v
        for n, v in kwds.items()
    }

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


def resolve_gear_alternative(func, args, kwds):
    errors = []
    for f, args, templates in get_gear_signatures(func, args, kwds):
        try:
            params = infer_params(args, templates,
                                  get_function_context_dict(f))
        except TypeMatchError:
            errors.append((f, *sys.exc_info()))
        else:
            return (f, params)

    raise MultiAlternativeError(errors)


def resolve_gear_call(func, args, kwds):
    args, kwds = form_gear_args(args, kwds, func)

    f, params = resolve_gear_alternative(func, args, kwds)

    return ir.CallExpr(f, args, kwds, params)


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

    # TODO: Sort this casting out
    signed = typeof(op1.dtype, Int) or typeof(op2.dtype, Int)
    if signed and typeof(op1.dtype, Uint):
        op1_compare = resolve_cast_func(op1, Int)
    if signed and typeof(op2.dtype, Uint):
        op2_compare = resolve_cast_func(op2, Int)

    cond = ir.BinOpExpr((op1_compare, op2_compare), ir.opc.Gt)
    return ir.ConditionalExpr(cond=cond, operands=(op1, op2))


def call_len(arg, **kwds):
    if isinstance(arg, ir.ConcatExpr):
        return ir.ResExpr(len(arg.operands))

    if isinstance(arg, ir.ResExpr):
        return ir.ResExpr(len(arg.val))

    raise Exception


def call_print(*arg, **kwds):
    pass


def call_int(arg, **kwds):
    # ignore cast
    if typeof(arg.dtype, (Uint, Int)):
        return arg
    elif typeof(arg.dtype, Integral):
        if arg.dtype.signed:
            return ir.CastExpr(arg, cast_to=Int[arg.dtype.width])
        else:
            return ir.CastExpr(arg, cast_to=Uint[arg.dtype.width])


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
    # return ir.SignalStmt(ir.SignalDef(obj), arg)
    return ir.AssignValue(obj, arg)


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


def call_isinstance(arg, dtype):
    if isinstance(dtype, ir.ResExpr):
        dtype = dtype.val

    if isinstance(arg, ir.ResExpr):
        return isinstance(arg.val, dtype)

    return ir.ResExpr(typeof(arg.dtype, dtype))


def call_is_type(arg):
    if not isinstance(arg, ir.ResExpr):
        return ir.res_false

    return ir.ResExpr(is_type(arg.val))


def call_typeof(arg, dtype):
    if isinstance(dtype, ir.ResExpr):
        dtype = dtype.val

    if not isinstance(arg, ir.ResExpr):
        return ir.res_false

    return ir.ResExpr(typeof(arg.val, dtype))


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


builtins = {
    gather:
    call_gather,
    all:
    call_all,
    max:
    call_max,
    clk:
    call_clk,
    int:
    call_int,
    len:
    call_len,
    print:
    call_print,
    type:
    call_type,
    isinstance:
    call_isinstance,
    is_type:
    call_is_type,
    typeof:
    call_typeof,
    div:
    call_div,
    floor:
    call_floor,
    Intf.empty:
    call_empty,
    Intf.get:
    call_get,
    Intf.get_nb:
    call_get_nb,
    cast:
    call_cast,
    signed:
    call_signed,
    QueueMeta.sub:
    call_sub,
    OutSig.write:
    outsig_write,
    Array.code:
    call_code,
    Tuple.code:
    call_code,
    code:
    call_code,
    qrange:
    call_qrange,
    range:
    call_range,
    enumerate:
    call_enumerate,
    breakpoint:
    call_breakpoint,
    saturate:
    lambda *args, **kwds: resolve_gear_call(saturate_gear.func, (), {
        'din': args[0],
        't': args[1]
    })
}

# TODO: Both bitwise and boolean operators will be mapped to bitwise HDL
# operators. Rework the mapping below.

int_ops = {
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


for op, name in int_ops.items():
    builtins[getattr(int, name)] = lambda a, b, x=op: ir.BinOpExpr((call_int(a), b), x)

compile_time_builtins = {
    all, max, int, len, type, isinstance, div, floor, cast, QueueMeta.sub,
    Array.code, Tuple.code, code, is_type, typeof
}


class Method:
    def __init__(self, func, val, cls):
        self.__func__ = func
        self.__self__ = val
        self.__dtype__ = cls

    def __call__(self, *args, **kwds):
        self.__func__(self.__self__, *args, **kwds)


class Super:
    def __init__(self, cls, val):
        self.cls = cls
        self.val = val

    def __getattribute__(self, name):
        cls = super().__getattribute__('cls')
        val = super().__getattribute__('val')
        for base in inspect.getmro(cls):
            if name in base.__dict__:
                if base is object:
                    return getattr(base, name)

                f = base.__dict__[name]
                if isinstance(val, ir.ResExpr):
                    f = partial(f, val.val)
                    # f = f.__get__(op1.val, base)
                else:
                    f = partial(f, val)
                    # f = f.__get__(base(), base)

                store_method_obj(f, val)

                return f
        else:
            raise AttributeError(name)


def get_class_that_defined_method(meth):
    if inspect.ismethod(meth):
        for cls in inspect.getmro(meth.__self__.__class__):
            if cls.__dict__.get(meth.__name__) is meth:
                return cls
        meth = meth.__func__  # fallback to __qualname__ parsing

    if isinstance(meth, Method):
        return meth.__dtype__

    if inspect.isfunction(meth):
        cls = getattr(
            inspect.getmodule(meth),
            meth.__qualname__.split('.<locals>', 1)[0].rsplit('.', 1)[0])
        if isinstance(cls, type):
            return cls

    return getattr(meth, '__objclass__',
                   None)  # handle special descriptor objects


def get_method_obj(f):
    ctx = registry('hls/ctx')[0]
    print(f'Get __self__ for {f}: {id(f)}')
    # TODO: Think about whether hash(repr(f)) is a unique way to reference a
    # method when I used id(f), it wasn't unique (garbage collection?). Maybe I
    # could hook somehow to garbage disposal of functions
    obj, wref = ctx.methods.get(id(f), (None, None))
    if wref is not None:
        if wref() is None:
            return None

    return obj


def store_method_obj(f, obj):
    ctx = registry('hls/ctx')[0]
    ctx.methods[id(f)] = (obj, weakref.ref(f))
    print(f'Storing {obj} for {f} under {id(f)}')


def func_from_method(f):
    if hasattr(f, '__func__'):
        return f.__func__

    return getattr(type(f.__self__), f.__name__)


def resolve_func(func, args, kwds, ctx):
    if is_type(func):
        if const_func_args(args, kwds):
            return resolve_compile_time(func, args, kwds)

        return resolve_cast_func(args[0], func)

    if isinstance(func, partial):
        args = func.args + tuple(args)
        func = func.func
    elif not inspect.isbuiltin(func) and hasattr(func, '__self__'):

        if get_method_obj(func) is not None:
            args = (get_method_obj(func), ) + tuple(args)
            func = func_from_method(func)
        elif func is super:
            if not isinstance(ctx, FuncContext):
                raise Expception(f'super() called outside a method function')

            f = ctx.funcref.func
            obj = ctx.ref('self')
            cls = get_class_that_defined_method(f).__base__

            return ir.ResExpr(Super(cls, obj))
        elif const_func_args(args, kwds):
            if func.__qualname__ == 'FixpnumberType.__add__':
                print('But not here?')

            return resolve_compile_time(func, args, kwds)
        elif is_type(func.__self__):
            if func.__name__ == 'decode':
                return ir.CastExpr(args[0], ir.ResExpr(func.__self__))
            else:
                breakpoint()
                raise Exception
        else:
            breakpoint()
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
    elif hasattr(func, 'dispatch'):
        if isinstance(args[0], ir.ResExpr) and is_type(args[0].val):
            # TODO: Reconsider why ResExpr returns None for type classes, which
            # makes this "if" necessary
            dtype = args[0].val.__class__
        else:
            dtype = args[0].dtype

        return resolve_func(func.dispatch(dtype), args, kwds, ctx)
    else:
        return parse_func_call(func, args, kwds, ctx)
        # return parse_func_call(orig_func, args, kwds, ctx)


@node_visitor(ast.Call)
def _(node, ctx: Context):
    name = visit_ast(node.func, ctx)

    assert isinstance(name, (ir.ResExpr, ir.AttrExpr))

    args, kwds = parse_func_args(node.args, node.keywords, ctx)

    if not isinstance(name, ir.ResExpr):
        return ir.CallExpr(name, args, kwds)

    func = name.val

    return resolve_func(func, args, kwds, ctx)
