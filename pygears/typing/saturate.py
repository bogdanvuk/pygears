from pygears.typing import typeof, Int
from .cast import cast


def int_saturate_resolver(val, cast_type, limits=None):
    val = cast(val, Int)
    if limits is None:
        limits = (cast_type.min + 1, cast_type.max)

    if val < limits[0]:
        return limits[0]
    elif val > limits[1]:
        return limits[1]
    else:
        return cast_type(val)


saturate_resolvers = {
    Int: int_saturate_resolver,
}


def saturate(val, cast_type, limits=None):
    for templ in saturate_resolvers:
        if typeof(cast_type, templ):
            return saturate_resolvers[templ](val, cast_type)
