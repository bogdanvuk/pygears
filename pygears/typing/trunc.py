from functools import singledispatch
from pygears.typing import typeof, Int, Fixp, Uint, Ufixp, is_type, Integral, Fixpnumber, Integer, code
from pygears.typing.uint import IntegerType, IntType, UintType
from pygears.typing.fixp import FixpnumberType, FixpType, UfixpType
from .cast import cast


@singledispatch
def type_trunc(cast_type, val):
    raise TypeError(
        f"Type '{repr(cast_type)}' unsupported, cannot truncate type '{val}' "
        f"of type '{repr(type(val))}'")


@type_trunc.register(IntegerType)
def integer_type_trunc_resolver(cast_type: IntegerType, dtype):
    if dtype is int:
        return cast_type

    if not is_type(dtype) or dtype.base != cast_type.base:
        raise TypeError(
            f"cannot truncate type '{repr(dtype)}' to a type '{repr(cast_type)}'"
            f" of a different base type")

    return cast_type


@type_trunc.register(FixpnumberType)
def fixp_type_trunc_resolver(cast_type: FixpnumberType, dtype):
    if not is_type(dtype) or dtype.base != cast_type.base:
        raise TypeError(
            f"cannot truncate type '{repr(dtype)}' to a type '{repr(cast_type)}'"
            f" of a different base type")

    return cast_type


@singledispatch
def value_trunc(cast_type, val):
    raise ValueError(
        f"Truncating to type '{repr(cast_type)}' unsupported, cannot truncate value '{val}' "
        f"of type '{repr(type(val))}'")


@value_trunc.register(FixpType)
def fixp_value_trunc_resolver(trunc_type: FixpType, val):
    bv = code(val, Uint)
    sign = bv >> (type(val).width - 1)

    if type(val).fract >= trunc_type.fract:
        bv_fract_trunc = bv >> (type(val).fract - trunc_type.fract)

    else:
        bv_fract_trunc = bv << (trunc_type.fract - type(val).fract)

    if type(val).integer >= trunc_type.integer:
        bv_res = (
            bv_fract_trunc & ((1 << (trunc_type.width - 1)) - 1) |
            (sign << (trunc_type.width - 1)))
    else:
        sign_exten = Uint[trunc_type.integer - type(val).integer].max if sign else 0
        bv_res = (sign_exten << (type(val).integer + trunc_type.fract)) | bv_fract_trunc

    return trunc_type.decode(bv_res)


@value_trunc.register(UfixpType)
def ufixp_value_trunc_resolver(trunc_type: UfixpType, val):
    if type(val).fract > trunc_type.fract:
        return trunc_type.decode(code(val, int) >> (type(val).fract - trunc_type.fract))
    else:
        return trunc_type.decode(code(val, int) << (trunc_type.fract - type(val).fract))


@value_trunc.register(IntType)
def int_value_trunc_resolver(trunc_type: IntType, val):
    bv = code(val, int)
    sign = bv >> (type(val).width - 1)

    if trunc_type.width <= type(val).width:
        bv_res = bv & ((1 << trunc_type.width) - 1) \
            | (sign << (trunc_type.width - 1))
    else:
        sign_exten = Uint[trunc_type.width - type(val).width].max if sign else 0
        bv_res = (sign_exten << type(val).width) | bv

    return trunc_type.decode(bv_res)


@value_trunc.register(UintType)
def uint_value_trunc_resolver(trunc_type: UintType, val):
    return trunc_type.decode(code(val, int) & ((1 << trunc_type.width) - 1))


def trunc(data, t):
    if is_type(data):
        return type_trunc(t, data)
    else:
        return value_trunc(type_trunc(t, type(data)), data)
