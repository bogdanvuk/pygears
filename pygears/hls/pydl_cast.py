from pygears.typing import Fixp, Fixpnumber, Integer, Tuple, Ufixp, Uint, typeof, Int, Union, cast
from . import nodes as expr
from pygears.typing import get_match_conds, TypeMatchError


def fixp_resolver(opexp, cast_to):
    val_dtype = opexp.dtype

    if typeof(val_dtype, Integer):
        other_cls = Fixp if val_dtype.signed else Ufixp
        val_dtype = other_cls[val_dtype.width, val_dtype.width]

    val_fract = val_dtype.fract
    fract = cast_to.fract

    if fract > val_fract:
        shift = expr.BinOpExpr([opexp, expr.ResExpr(Uint(fract - val_fract))], expr.opc.LShift)
    else:
        shift = expr.BinOpExpr([opexp, expr.ResExpr(Uint(val_fract - fract))], expr.opc.RShift)

    return expr.CastExpr(shift, cast_to)


def subscript(opexp, index):
    if not isinstance(index, slice) and isinstance(opexp, expr.ConcatExpr):
        return opexp.operands[index]
    else:
        return expr.SubscriptExpr(opexp, index)


def tuple_resolver(opexp, cast_to):
    cast_to = cast(opexp.dtype, cast_to)

    cast_fields = []
    for i in range(len(opexp.dtype)):
        field = subscript(opexp, i)
        cast_fields.append(resolve_cast_func(field, cast_to[i]))

    return expr.ConcatExpr(cast_fields)


def union_resolver(opexp, cast_to):
    cast_to = cast(opexp.dtype, cast_to)

    op_data = subscript(opexp, 0)
    op_ctrl = subscript(opexp, 1)

    cast_fields = []
    uint_data = expr.CastExpr(op_data, Uint[op_data.dtype.width])
    cast_fields.append(resolve_cast_func(uint_data, cast_to.data))

    cast_fields.append(resolve_cast_func(op_ctrl, cast_to.ctrl))

    return expr.CastExpr(expr.ConcatExpr(cast_fields), cast_to)


def uint_resolver(opexp, cast_to):
    return expr.CastExpr(opexp, cast(opexp.dtype, cast_to))


def int_resolver(opexp, cast_to):
    cast_to = cast(opexp.dtype, cast_to)
    if typeof(opexp.dtype, Uint):
        opexp = expr.CastExpr(opexp, Uint[cast_to.width])

    return expr.CastExpr(opexp, cast_to)


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
            get_match_conds(dtype, templ)
            return resolvers[templ](opexp, dtype)
        except TypeMatchError:
            continue

    return expr.CastExpr(operand=opexp, cast_to=cast(opexp.dtype, dtype))
