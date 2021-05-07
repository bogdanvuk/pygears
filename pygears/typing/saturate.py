from functools import singledispatch
from pygears.typing import typeof, Int, Fixp, Uint, Ufixp, is_type, Integer, Fixpnumber, Integral, trunc
from pygears.typing.uint import IntegerType, IntegralType
from pygears.typing.fixp import FixpnumberType
from .cast import cast
from . import code


@singledispatch
def type_saturate(cast_type, val):
    raise TypeError(f"Type '{repr(cast_type)}' unsupported, cannot saturate type '{val}' "
                    f"of type '{repr(type(val))}'")


@type_saturate.register(IntegerType)
def integral_type_saturate_resolver(cast_type, dtype):
    if dtype is not int and not typeof(dtype, Integer):
        raise TypeError(
            f"cannot saturate '{repr(dtype)}' to a different base type '{repr(cast_type)}'")

    return cast_type


@type_saturate.register(FixpnumberType)
def fixp_type_saturate_resolver(cast_type, dtype):
    if not typeof(dtype, Fixpnumber):
        raise TypeError(
            f"cannot saturate '{repr(dtype)}' to a different base type '{repr(cast_type)}'")

    if dtype.fract != cast_type.fract:
        raise TypeError(
            f"cannot saturate fixed point type '{repr(dtype)}' to a type '{repr(cast_type)}'"
            f" with a different fractional size ({dtype.fract} != {cast_type.fract})")

    return cast_type


@singledispatch
def value_saturate(cast_type, val, limits=None):
    raise ValueError(
        f"Saturating to type '{repr(cast_type)}' unsupported, cannot saturate value '{val}' "
        f"of type '{repr(type(val))}'")


@value_saturate.register(IntegralType)
def integral_saturate_resolver(t, data: Integral, limits=None):
    if not is_type(type(data)) and isinstance(data, int):
        conv_data = Integer(data)
    else:
        conv_data = data

    idin = code(data)

    if type(conv_data).signed == t.signed and type(conv_data).width <= t.width:
        if type(conv_data).signed:
            sign = code(data, int) >> (type(conv_data).width - 1)
            sign_exten = Uint[t.width - type(conv_data).width].max if sign else 0
            return t.decode((sign_exten << type(conv_data).width) | code(data, int))
        else:
            return code(conv_data, t)
    elif type(conv_data).signed and not t.signed:
        if idin[t.width:] == 0:
            return code(conv_data, t)
        elif conv_data < 0:
            return 0
        else:
            return t.max
    elif type(conv_data).signed and t.signed:
        # TODO: This 0 is not typecast, check why that happens
        if ((idin[t.width - 1:] == 0)
                or (idin[t.width - 1:] == Uint[type(conv_data).width - t.width + 1].max)):
            return code(conv_data, t)
        elif idin[-1]:
            return t.min
        else:
            return t.max
    else:
        if type(conv_data).width <= t.width or idin[t.width:] == 0:
            return code(conv_data, t)
        else:
            return t.max


def saturate(data, t, limits=None):
    if is_type(data):
        return type_saturate(t, data)
    else:
        return value_saturate(type_saturate(t, type(data)), data, limits)
