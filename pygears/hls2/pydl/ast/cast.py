from pygears.typing import Fixp, Fixpnumber, Integer, Tuple, Ufixp, Uint, typeof, Int, Union, cast
from . import nodes
from pygears.core.type_match import type_match, TypeMatchError


def fixp_resolver(opexp, cast_to):
    val_dtype = opexp.dtype

    if typeof(val_dtype, Integer):
        other_cls = Fixp if val_dtype.signed else Ufixp
        val_dtype = other_cls[val_dtype.width, val_dtype.width]

    val_fract = val_dtype.fract
    fract = cast_to.fract

    if fract > val_fract:
        shift = nodes.BinOpExpr([opexp, nodes.ResExpr(Uint(fract - val_fract))], nodes.opc.LShift)
    else:
        shift = nodes.BinOpExpr([opexp, nodes.ResExpr(Uint(val_fract - fract))], nodes.opc.RShift)

    return nodes.CastExpr(shift, cast_to)


def subscript(opexp, index):
    if not isinstance(index, slice) and isinstance(opexp, nodes.ConcatExpr):
        return opexp.operands[index]
    else:
        return nodes.SubscriptExpr(opexp, nodes.ResExpr(index))


def tuple_resolver(opexp, cast_to):
    cast_to = cast(opexp.dtype, cast_to)

    cast_fields = []
    for i in range(len(opexp.dtype)):
        field = subscript(opexp, i)
        cast_fields.append(resolve_cast_func(field, cast_to[i]))

    return nodes.ConcatExpr(cast_fields)


def union_resolver(opexp, cast_to):
    cast_to = cast(opexp.dtype, cast_to)

    op_data = subscript(opexp, 0)
    op_ctrl = subscript(opexp, 1)

    cast_fields = []
    uint_data = nodes.CastExpr(op_data, Uint[op_data.dtype.width])
    cast_fields.append(resolve_cast_func(uint_data, cast_to.data))

    cast_fields.append(resolve_cast_func(op_ctrl, cast_to.ctrl))

    return nodes.CastExpr(nodes.ConcatExpr(cast_fields), cast_to)


def uint_resolver(opexp, cast_to):
    return nodes.CastExpr(opexp, cast(opexp.dtype, cast_to))


def int_resolver(opexp, cast_to):
    cast_to = cast(opexp.dtype, cast_to)
    if typeof(opexp.dtype, Uint):
        opexp = nodes.CastExpr(opexp, Uint[cast_to.width])

    return nodes.CastExpr(opexp, cast_to)


resolvers = {
    Fixpnumber: fixp_resolver,
    Tuple: tuple_resolver,
    Int: int_resolver,
    Uint: uint_resolver,
    Union: union_resolver
}


def resolve_cast_func(opexp, dtype):
    if opexp.dtype == dtype:
        return opexp

    for templ in resolvers:
        try:
            type_match(dtype, templ)
            return resolvers[templ](opexp, dtype)
        except TypeMatchError:
            continue

    return nodes.CastExpr(operand=opexp, cast_to=cast(opexp.dtype, dtype))
