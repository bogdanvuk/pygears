from pygears.typing import typeof, Int, Fixp, Uint, Ufixp
from .cast import cast


def integral_saturate_resolver(val, cast_type, limits=None):
    val = cast(val, cast_type.base)
    if limits is None:
        if cast_type.signed:
            limits = (-cast_type.max, cast_type.max)
        else:
            limits = (cast_type(0), cast_type.max)

    print(f'val: {val} ({float(val)}), limits: {limits}')

    if val < limits[0]:
        return limits[0]
    elif val > limits[1]:
        return limits[1]
    else:
        return cast_type(val)


saturate_resolvers = {
    Int: integral_saturate_resolver,
    Fixp: integral_saturate_resolver,
    Uint: integral_saturate_resolver,
    Ufixp: integral_saturate_resolver,
}


def saturate(val, cast_type, limits=None):
    for templ in saturate_resolvers:
        if typeof(cast_type, templ):
            return saturate_resolvers[templ](val, cast_type)

    raise ValueError(f"Type '{repr(cast_type)}' unsupported, cannot saturate value '{val}' "
                     f"of type '{repr(type(val))}'")
