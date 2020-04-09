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


@type_trunc.register
def integer_type_trunc_resolver(cast_type: IntegerType, dtype):
    if dtype.base != cast_type.base:
        raise TypeError(
            f"cannot truncate type '{repr(dtype)}' to a type '{repr(cast_type)}'"
            f" of a different base type")

    if cast_type.width > dtype.width:
        return dtype

    return cast_type


@type_trunc.register
def fixp_type_trunc_resolver(cast_type: FixpnumberType, dtype):
    if dtype.base != cast_type.base:
        raise TypeError(
            f"cannot truncate type '{repr(dtype)}' to a type '{repr(cast_type)}'"
            f" of a different base type")

    fract = cast_type.fract
    if cast_type.fract > dtype.fract:
        fract = dtype.fract

    integer = cast_type.integer
    if cast_type.integer > dtype.integer:
        integer = dtype.integer

    return cast_type.base[integer, integer + fract]


@singledispatch
def value_trunc(cast_type, val):
    raise ValueError(
        f"Type '{repr(cast_type)}' unsupported, cannot truncate value '{val}' "
        f"of type '{repr(type(val))}'")


@value_trunc.register
def fixp_value_trunc_resolver(trunc_type: FixpType, val):
    bv = code(val, int)
    sign = bv >> (type(val).width - 1)

    bv_fract_trunc = bv >> (type(val).fract - trunc_type.fract)

    bv_res = (bv_fract_trunc & ((1 << trunc_type.width) - 1) |
              (sign << (trunc_type.width - 1)))

    return trunc_type.decode(bv_res)


@value_trunc.register
def ufixp_value_trunc_resolver(trunc_type: UfixpType, val):
    return trunc_type.decode(
        code(val, int) >> (type(val).fract - trunc_type.fract))


@value_trunc.register
def int_value_trunc_resolver(trunc_type: IntType, val):
    bv = code(val, int)
    sign = bv >> (type(val).width - 1)

    bv_res = bv & ((1 << trunc_type.width) - 1) | (sign <<
                                                   (trunc_type.width - 1))

    return trunc_type.decode(bv_res)


@value_trunc.register
def uint_value_trunc_resolver(trunc_type: UintType, val):
    return trunc_type.decode(code(val, int) & ((1 << trunc_type.width) - 1))


def trunc(data, cast_type):
    if is_type(data):
        return type_trunc(data, cast_type)
    else:
        return value_trunc(type_trunc(type(data), cast_type), data)
