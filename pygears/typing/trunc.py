from pygears.typing import typeof, Int, Fixp, Uint, Ufixp, is_type, Integral, Fixpnumber, Integer
from .cast import cast


def integer_type_trunc_resolver(dtype, cast_type):
    if dtype.base != cast_type.base:
        raise TypeError(
            f"cannot truncate type '{repr(dtype)}' to a type '{repr(cast_type)}'"
            f" of a different base type")

    if cast_type.width > dtype.width:
        return dtype

    return cast_type


def fixp_type_trunc_resolver(dtype, cast_type):
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


type_trunc_resolvers = {
    Fixpnumber: fixp_type_trunc_resolver,
    Integer: integer_type_trunc_resolver,
}


def type_trunc(val, cast_type):
    for templ in type_trunc_resolvers:
        if typeof(cast_type, templ):
            return type_trunc_resolvers[templ](val, cast_type)

    raise TypeError(
        f"Type '{repr(cast_type)}' unsupported, cannot truncate type '{val}' "
        f"of type '{repr(type(val))}'")


def fixp_value_trunc_resolver(val, cast_type):
    val_type = type(val)
    res_type = type_trunc(val_type, cast_type)

    bv = val.code()
    sign = bv >> (val_type.width - 1)

    bv_fract_trunc = bv >> (val_type.fract - cast_type.fract)

    bv_res = (bv_fract_trunc & ((1 << res_type.width) - 1) |
              (sign << (res_type.width - 1)))

    return res_type.decode(bv_res)


def ufixp_value_trunc_resolver(val, cast_type):
    val_type = type(val)
    res_type = type_trunc(val_type, cast_type)

    return res_type.decode(val.code() >> (val_type.fract - cast_type.fract))


def int_value_trunc_resolver(val, cast_type):
    val_type = type(val)
    res_type = type_trunc(val_type, cast_type)

    bv = val.code()
    sign = bv >> (val_type.width - 1)

    bv_res = bv & ((1 << res_type.width) - 1) | (sign << (res_type.width - 1))

    return res_type.decode(bv_res)


def uint_value_trunc_resolver(val, cast_type):
    val_type = type(val)
    res_type = type_trunc(val_type, cast_type)

    return res_type.decode(val.code() & ((1 << res_type.width) - 1))


value_trunc_resolvers = {
    Fixp: fixp_value_trunc_resolver,
    Ufixp: ufixp_value_trunc_resolver,
    Int: int_value_trunc_resolver,
    Uint: uint_value_trunc_resolver,
}


def value_trunc(val, cast_type):
    for templ in value_trunc_resolvers:
        if typeof(cast_type, templ):
            return value_trunc_resolvers[templ](val, cast_type)

    raise ValueError(
        f"Type '{repr(cast_type)}' unsupported, cannot truncate value '{val}' "
        f"of type '{repr(type(val))}'")


def trunc(data, cast_type):
    if is_type(data):
        return type_trunc(data, cast_type)
    else:
        sat_type = type_trunc(type(data), cast_type)
        return value_trunc(data, sat_type)
