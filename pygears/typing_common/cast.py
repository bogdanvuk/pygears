from pygears.typing import TypingNamespacePlugin, typeof
from pygears.typing import Int, Uint, Queue, Tuple, Union


def cast(dtype, cast_type):
    if typeof(cast_type, Int) and (not cast_type.is_specified()):
        if issubclass(dtype, Uint):
            return Int[int(dtype) + 1]
        elif issubclass(dtype, Int):
            return dtype
        else:
            return Int[int(dtype)]
    elif typeof(cast_type, Tuple):
        if not cast_type.is_specified():
            if typeof(dtype, Queue) or typeof(dtype, Union):
                return Tuple[dtype[0], dtype[1:]]
        else:
            return cast_type
    else:
        return cast_type


class CastTypePlugin(TypingNamespacePlugin):
    @classmethod
    def bind(cls):
        cls.registry['TypeArithNamespace']['cast'] = cast
