from pygears.conf import safe_bind
from pygears.typing.base import typeof, is_type
from pygears.typing import Int, Uint, Queue, Tuple, Union, Array, Integer, CoreTypesPlugin, Fixpnumber
from pygears.conf.log import gear_log
from .type_match import type_match, TypeMatchError


def uint_cast_resolver(dtype, cast_type):
    if not cast_type.specified:
        return Uint[int(dtype)]

    return cast_type


def int_cast_resolver(dtype, cast_type):
    if not cast_type.specified:
        if typeof(dtype, Uint):
            return Int[int(dtype) + 1]
        elif typeof(dtype, Int):
            return dtype
        else:
            return Int[int(dtype)]

    return cast_type


def tuple_cast_resolver(dtype, cast_type):
    if not cast_type.specified:
        if typeof(dtype, Queue) or typeof(dtype, Union):
            return Tuple[dtype[0], dtype[1]]
        elif typeof(dtype, Tuple):
            return dtype
        elif typeof(dtype, Array):
            return Tuple[(dtype[0], ) * len(dtype)]

    return cast_type


def union_cast_resolver(dtype, cast_type):
    if (typeof(dtype, Tuple) and len(dtype) == 2 and not cast_type.specified):

        res = Union[(dtype[0], ) * (2**int(dtype[1]))]

        if int(dtype[1]) > 6:
            gear_log().warning(
                f'Casting to large Union with {2**int(dtype[1])}'
                f' subtypes from {dtype}')

        return res

    return cast_type


cast_resolvers = {
    Uint: uint_cast_resolver,
    Int: int_cast_resolver,
    Tuple: tuple_cast_resolver,
    Union: union_cast_resolver
}


def type_cast(dtype, cast_type):
    for templ in cast_resolvers:
        try:
            type_match(cast_type, templ)
            return cast_resolvers[templ](dtype, cast_type)
        except TypeMatchError:
            continue

    return cast_type


# def type_cast(dtype, cast_type):
#     if typeof(cast_type, Int) and (not cast_type.specified):
#         if typeof(dtype, Uint):
#             return Int[int(dtype) + 1]
#         elif typeof(dtype, Int):
#             return dtype
#         else:
#             return Int[int(dtype)]
#     if typeof(cast_type, Uint) and (not cast_type.specified):
#         if typeof(dtype, Int):
#             return Uint[int(dtype) - 1]
#         else:
#             return Uint[int(dtype)]
#     elif typeof(cast_type, Tuple) and (not cast_type.specified):
#         if typeof(dtype, Queue) or typeof(dtype, Union):
#             return Tuple[dtype[0], dtype[1]]
#         elif typeof(dtype, Tuple):
#             return dtype
#         elif typeof(dtype, Array):
#             return Tuple[(dtype[0], ) * len(dtype)]
#     elif (typeof(cast_type, Union) and typeof(dtype, Tuple) and len(dtype) == 2
#           and not cast_type.specified):

#         res = Union[(dtype[0], ) * (2**int(dtype[1]))]

#         if int(dtype[1]) > 6:
#             gear_log().warning(
#                 f'Casting to large Union with {2**int(dtype[1])}'
#                 f' subtypes from {dtype}')

#         return res

#     else:
#         return cast_type


def value_cast(val, cast_type):
    if typeof(cast_type, Int) and (not cast_type.specified) and typeof(
            type(val), (Uint, Int)):
        dout = cast_type(val)
    elif typeof(cast_type, Integer) and typeof(type(val), Integer):
        if not cast_type.specified:
            cast_type = cast_type[val.width]

        tout_range = (1 << int(cast_type))
        val = int(val) & (tout_range - 1)

        if typeof(cast_type, Int):
            max_uint = tout_range / 2 - 1
            if val > max_uint:
                val -= tout_range

        dout = cast_type(val)
    elif typeof(cast_type, Tuple) and typeof(
            type(val), Queue) and not cast_type.specified:
        dout = cast_type((val[0], val[1:]))
    elif (typeof(cast_type, Union) and typeof(type(val), Tuple)
          and len(type(val)) == 2 and not cast_type.specified):
        dout = type_cast(type(val), cast_type)(val)
    elif (typeof(cast_type, Fixpnumber) and typeof(type(val), Fixpnumber)):
        dout = cast_type(val)
    else:
        dout = cast_type.decode(int(val))

    return dout


def cast(data, cast_type):
    if is_type(data):
        return type_cast(data, cast_type)
    else:
        return value_cast(data, cast_type)


class CastCoreTypesPlugin(CoreTypesPlugin):
    @classmethod
    def bind(cls):
        safe_bind('gear/type_arith/cast', cast)
