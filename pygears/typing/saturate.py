from pygears.typing import typeof, Int, Fixp, Uint, Ufixp, is_type, Integer, Fixpnumber
from .cast import cast


def integral_type_saturate_resolver(dtype, cast_type):
    if dtype is not int and not typeof(dtype, Integer):
        raise TypeError(
            f"cannot saturate '{repr(dtype)}' to a different base type '{repr(cast_type)}'")

    return cast_type


def fixp_type_saturate_resolver(dtype, cast_type):
    if not typeof(dtype, Fixpnumber):
        raise TypeError(
            f"cannot saturate '{repr(dtype)}' to a different base type '{repr(cast_type)}'")

    if dtype.fract != cast_type.fract:
        raise TypeError(
            f"cannot saturate fixed point type '{repr(dtype)}' to a type '{repr(cast_type)}'"
            f" with a different fractional size ({dtype.fract} != {cast_type.fract})")

    return cast_type


type_saturate_resolvers = {
    Int: integral_type_saturate_resolver,
    Fixp: fixp_type_saturate_resolver,
    Uint: integral_type_saturate_resolver,
    Ufixp: fixp_type_saturate_resolver,
}


def type_saturate(val, cast_type, limits=None):
    for templ in type_saturate_resolvers:
        if typeof(cast_type, templ):
            return type_saturate_resolvers[templ](val, cast_type)

    raise TypeError(
        f"Type '{repr(cast_type)}' unsupported, cannot saturate type '{val}'"
        f" of type '{repr(type(val))}'")


def integral_value_saturate_resolver(val, cast_type, limits=None):
    val = cast(val, cast_type.base)
    if limits is None:
        if cast_type.signed:
            limits = (cast_type.min, cast_type.max)
        else:
            limits = (cast_type(0), cast_type.max)

    if val < limits[0]:
        return limits[0]
    elif val > limits[1]:
        return limits[1]
    else:
        return cast_type(val)


value_saturate_resolvers = {
    Int: integral_value_saturate_resolver,
    Fixp: integral_value_saturate_resolver,
    Uint: integral_value_saturate_resolver,
    Ufixp: integral_value_saturate_resolver,
}


def value_saturate(val, cast_type, limits=None):
    for templ in value_saturate_resolvers:
        if typeof(cast_type, templ):
            return value_saturate_resolvers[templ](val, cast_type, limits)

    raise ValueError(
        f"Type '{repr(cast_type)}' unsupported, cannot saturate value '{val}'"
        f" of type '{repr(type(val))}'")


def saturate(data, t, limits=None):
    if is_type(data):
        return type_saturate(data, t, limits)
    else:
        sat_type = type_saturate(type(data), t, limits)
        return value_saturate(data, sat_type, limits)
