from pygears.typing import Fixp, Fixpnumber, Integer, Tuple, Ufixp, Uint, typeof, Int, Union, cast, Array, Queue, Maybe, Bool
from . import ir
from pygears.typing import get_match_conds, TypeMatchError


def fixp_resolver(opexp, cast_to):
    cast_to = cast(opexp.dtype, cast_to)

    val_dtype = opexp.dtype

    if typeof(val_dtype, Integer):
        other_cls = Fixp if val_dtype.signed else Ufixp
        val_dtype = other_cls[val_dtype.width, val_dtype.width]

    if cast_to is Fixpnumber:
        return ir.CastExpr(opexp, val_dtype)

    val_fract = val_dtype.fract
    fract = cast_to.fract

    if val_dtype.signed:
        opexp = ir.CastExpr(opexp, Int[val_dtype.width])
    else:
        opexp = ir.CastExpr(opexp, Uint[val_dtype.width])

    if fract > val_fract:
        shift = ir.BinOpExpr([opexp, ir.ResExpr(Uint(fract - val_fract))], ir.opc.LShift)
    else:
        shift = ir.BinOpExpr([opexp, ir.ResExpr(Uint(val_fract - fract))], ir.opc.RShift)

    return ir.CastExpr(shift, cast_to)


def subscript(opexp, index):
    if not isinstance(index, slice) and isinstance(opexp, ir.ConcatExpr):
        return opexp.operands[index]
    else:
        return ir.SubscriptExpr(opexp, ir.ResExpr(index))


def tuple_resolver(opexp, cast_to):
    cast_to = cast(opexp.dtype, cast_to)

    cast_fields = []
    for i in range(len(opexp.dtype)):
        field = subscript(opexp, i)
        cast_fields.append(resolve_cast_func(field, cast_to[i]))

    return ir.ConcatExpr(cast_fields)


def queue_resolver(opexp, cast_to):
    cast_to = cast(opexp.dtype, cast_to)

    if cast_to == opexp.dtype:
        return opexp

    return ir.CastExpr(
        ir.ConcatExpr([resolve_cast_func(subscript(opexp, 0), cast_to.data), subscript(opexp, 1)]),
        cast_to)


def array_resolver(opexp, cast_to):
    cast_to = cast(opexp.dtype, cast_to)

    dlen, clen = len(opexp.dtype), len(cast_to)

    if dlen == clen:
        cast_fields = []
        for i in range(len(opexp.dtype)):
            field = subscript(opexp, i)
            cast_fields.append(resolve_cast_func(field, cast_to.data))
    else:
        elen = len(cast_to.data)
        cast_fields = []
        for i in range(len(cast_to)):
            field = subscript(opexp, slice(elen*i, elen*(i+1)))
            cast_fields.append(resolve_cast_func(field, cast_to.data))

    return ir.ConcatExpr(cast_fields)


def union_resolver(opexp, cast_to):
    cast_to = cast(opexp.dtype, cast_to)

    op_data = subscript(opexp, 0)
    op_ctrl = subscript(opexp, 1)

    cast_fields = []
    uint_data = ir.CastExpr(op_data, Uint[op_data.dtype.width])
    cast_fields.append(resolve_cast_func(uint_data, cast_to.data))

    cast_fields.append(resolve_cast_func(op_ctrl, cast_to.ctrl))

    return ir.CastExpr(ir.ConcatExpr(cast_fields), cast_to)


def uint_resolver(opexp, cast_to):
    cast_to = cast(opexp.dtype, cast_to)

    if typeof(opexp.dtype, Ufixp):
        if opexp.dtype.fract >= 0:
            opexp = ir.BinOpExpr((opexp, ir.ResExpr(opexp.dtype.fract)), ir.opc.RShift)
        else:
            opexp = ir.BinOpExpr((opexp, ir.ResExpr(-opexp.dtype.fract)), ir.opc.LShift)

    return ir.CastExpr(opexp, cast_to)


def int_resolver(opexp, cast_to):
    cast_to = cast(opexp.dtype, cast_to)
    if typeof(opexp.dtype, Uint):
        opexp = ir.CastExpr(opexp, Uint[cast_to.width])

    return ir.CastExpr(opexp, cast_to)


# # TODO: Generalize this to any Union
# def maybe_resolver(opexp, cast_to):
#     if cast_to.specified and opexp.dtype == cast_to.dtype:
#         data = ir.CastExpr(resolve_cast_func(opexp, cast_to.dtype), cast_to[0])
#         return ir.CastExpr(ir.ConcatExpr([data, ir.ResExpr(Bool(True))]), cast_to)

#     cast_to = cast(opexp.dtype, cast_to)

#     if opexp.dtype == cast_to.dtype:
#         data = ir.CastExpr(resolve_cast_func(opexp, cast_to.dtype), cast_to[0])
#         return ir.CastExpr(ir.ConcatExpr([data, ir.ResExpr(Bool(True))]), cast_to)
#     elif typeof(opexp.dtype, Tuple):
#         data = resolve_cast_func(ir.SubscriptExpr(opexp, ir.ResExpr(0)), cast_to.dtype)
#         ctrl = resolve_cast_func(ir.SubscriptExpr(opexp, ir.ResExpr(1)), cast_to[1])
#         return ir.CastExpr(ir.ConcatExpr([data, ctrl]), cast_to)
#     elif typeof(opexp.dtype, Union):
#         return ir.CastExpr(opexp, cast_to)
#     else:
#         breakpoint()


def maybe_resolver(opexp, cast_to):
    cast_to = cast(opexp.dtype, cast_to)

    if typeof(opexp.dtype, Tuple):
        data = resolve_cast_func(ir.SubscriptExpr(opexp, ir.ResExpr(0)), cast_to.dtype)
        ctrl = resolve_cast_func(ir.SubscriptExpr(opexp, ir.ResExpr(1)), cast_to[1])
        return ir.CastExpr(ir.ConcatExpr([data, ctrl]), cast_to)
    elif typeof(opexp.dtype, Union):
        return ir.CastExpr(opexp, cast_to)
    else:
        breakpoint()

resolvers = {
    Fixpnumber: fixp_resolver,
    Tuple: tuple_resolver,
    Queue: queue_resolver,
    Array: array_resolver,
    Int: int_resolver,
    Uint: uint_resolver,
    Maybe: maybe_resolver, # Has to go before Union to be detected!
    Union: union_resolver,
}


def resolve_cast_func(opexp, dtype):
    if opexp.dtype == dtype:
        return opexp

    for templ in resolvers:
        try:
            get_match_conds(dtype, templ)
            return resolvers[templ](opexp, dtype)
        except TypeMatchError:
            continue

    return ir.CastExpr(operand=opexp, cast_to=cast(opexp.dtype, dtype))
