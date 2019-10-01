from pygears.conf import safe_bind
from pygears.typing.base import typeof, is_type
from pygears.typing import Int, Uint, Queue, Tuple, Union, Array, Integer
from pygears.typing import CoreTypesPlugin, Fixpnumber, Float, Number, Fixp
from pygears.conf.log import gear_log
from .type_match import type_match, TypeMatchError


def uint_type_cast_resolver(dtype, cast_type):
    if not cast_type.specified:
        return Uint[int(dtype)]

    return cast_type


def float_type_cast_resolver(dtype, cast_type):
    if typeof(dtype, Number):
        return cast_type

    raise TypeMatchError


def int_type_cast_resolver(dtype, cast_type):
    if not cast_type.specified:
        if typeof(dtype, Uint):
            return Int[int(dtype) + 1]
        elif typeof(dtype, Int):
            return dtype
        else:
            return Int[int(dtype)]

    return cast_type


def tuple_type_cast_resolver(dtype, cast_type):
    if not cast_type.specified:
        if typeof(dtype, Queue) or typeof(dtype, Union):
            return Tuple[dtype[0], dtype[1]]
        elif typeof(dtype, Tuple):
            return dtype
        elif typeof(dtype, Array):
            return Tuple[(dtype[0], ) * len(dtype)]

    return cast_type


def union_type_cast_resolver(dtype, cast_type):
    if (typeof(dtype, Tuple) and len(dtype) == 2 and not cast_type.specified):

        res = Union[(dtype[0], ) * (2**int(dtype[1]))]

        if int(dtype[1]) > 6:
            gear_log().warning(
                f'Casting to large Union with {2**int(dtype[1])}'
                f' subtypes from {dtype}')

        return res

    return cast_type


type_cast_resolvers = {
    Uint: uint_type_cast_resolver,
    Int: int_type_cast_resolver,
    Tuple: tuple_type_cast_resolver,
    Union: union_type_cast_resolver,
    Float: float_type_cast_resolver,
}


def type_cast(dtype, cast_type):
    for templ in type_cast_resolvers:
        try:
            type_match(cast_type, templ)
            return type_cast_resolvers[templ](dtype, cast_type)
        except TypeMatchError:
            continue

    return cast_type


def integer_value_cast_resolver(val, cast_type):
    if typeof(type(val), Integer):
        if not cast_type.specified:
            cast_type = cast_type[val.width]

        tout_range = (1 << int(cast_type))
        val = int(val) & (tout_range - 1)

        if typeof(cast_type, Int):
            max_uint = tout_range / 2 - 1
            if val > max_uint:
                val -= tout_range

        return cast_type(val)

    raise TypeMatchError


def int_value_cast_resolver(val, cast_type):
    if (not cast_type.specified) and typeof(type(val), (Uint, Int)):
        return cast_type(val)

    raise TypeMatchError


def tuple_value_cast_resolver(val, cast_type):
    if typeof(type(val), Queue) and not cast_type.specified:
        return cast_type((val[0], val[1:]))

    raise TypeMatchError


def union_value_cast_resolver(val, cast_type):
    if (typeof(type(val), Tuple) and len(type(val)) == 2
            and not cast_type.specified):
        return type_cast(type(val), cast_type)(val)

    raise TypeMatchError


def fixpnumber_value_cast_resolver(val, cast_type):
    if typeof(type(val), (Fixpnumber, Float)):
        return cast_type(val)

    raise TypeMatchError


def float_value_cast_resolver(val, cast_type):
    if typeof(type(val), (int, float, Number)):
        return cast_type(val)

    raise Exception(
        f'Only numbers can be converted to Float, not {val} of the type'
        f' {repr(type(val))}')


value_cast_resolvers = {
    Int: int_value_cast_resolver,
    Integer: integer_value_cast_resolver,
    Tuple: tuple_value_cast_resolver,
    Union: union_value_cast_resolver,
    Float: float_value_cast_resolver,
    Fixpnumber: fixpnumber_value_cast_resolver
}


def value_cast(val, cast_type):
    for templ in value_cast_resolvers:
        try:
            type_match(cast_type, templ)
            return value_cast_resolvers[templ](val, cast_type)
        except TypeMatchError:
            continue

    return cast_type.decode(int(val))


def cast(data, cast_type):
    if is_type(data):
        return type_cast(data, cast_type)
    else:
        return value_cast(data, cast_type)


def signed(dtype_or_val):
    if dtype_or_val.signed:
        return dtype_or_val

    if is_type(dtype_or_val):
        if typeof(dtype_or_val, Uint):
            return cast(dtype_or_val, Int)


class CastCoreTypesPlugin(CoreTypesPlugin):
    @classmethod
    def bind(cls):
        safe_bind('gear/type_arith/cast', cast)
