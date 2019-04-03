from pygears.conf import safe_bind
from .base import typeof, is_type
from . import Int, Uint, Queue, Tuple, Union, Array, Integer
from pygears.conf.log import gear_log


def type_cast(dtype, cast_type):
    if typeof(cast_type, Int) and (not cast_type.is_specified()):
        if typeof(dtype, Uint):
            return Int[int(dtype) + 1]
        elif typeof(dtype, Int):
            return dtype
        else:
            return Int[int(dtype)]
    if typeof(cast_type, Uint) and (not cast_type.is_specified()):
        if typeof(dtype, Int):
            return Uint[int(dtype) - 1]
        else:
            return Uint[int(dtype)]
    elif typeof(cast_type, Tuple) and (not cast_type.is_specified()):
        if typeof(dtype, Queue) or typeof(dtype, Union):
            return Tuple[dtype[0], dtype[1]]
        elif typeof(dtype, Tuple):
            return dtype
        elif typeof(dtype, Array):
            return Tuple[(dtype[0], ) * len(dtype)]
    elif (typeof(cast_type, Union) and typeof(dtype, Tuple) and len(dtype) == 2
          and not cast_type.is_specified()):

        res = Union[(dtype[0], ) * (2**int(dtype[1]))]

        if int(dtype[1]) > 6:
            gear_log().warning(
                f'Casting to large Union with {2**int(dtype[1])}'
                f' subtypes from {dtype}'
            )

        return res

    else:
        return cast_type


def value_cast(val, cast_type):
    if typeof(cast_type, Int) and (not cast_type.is_specified()) and typeof(
            type(val), (Uint, Int)):
        dout = cast_type(val)
    elif typeof(cast_type, Integer) and typeof(type(val), Integer):
        tout_range = (1 << int(cast_type))
        val = int(val) & (tout_range - 1)

        if typeof(cast_type, Int):
            max_uint = tout_range / 2 - 1
            if val > max_uint:
                val -= tout_range

        dout = cast_type(val)
    elif typeof(cast_type, Tuple) and typeof(
            type(val), Queue) and not cast_type.is_specified():
        dout = cast_type((val[0], val[1:]))
    elif (typeof(cast_type, Union) and typeof(type(val), Tuple)
          and len(type(val)) == 2 and not cast_type.is_specified()):
        pass
    else:
        dout = cast_type.decode(int(val))

    return dout


def cast(data, cast_type):
    if is_type(data):
        return type_cast(data, cast_type)
    else:
        return value_cast(data, cast_type)
