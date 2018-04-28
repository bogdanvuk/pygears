from pygears.typing import TypingNamespacePlugin, Int, Uint, Queue, Tuple


def cast(dtype, cast_type):
    if issubclass(cast_type, Int) and (not cast_type.is_specified()):
        if issubclass(dtype, Uint):
            return Int[int(dtype) + 1]
        elif issubclass(dtype, Int):
            return dtype
    elif issubclass(cast_type, Tuple) and issubclass(dtype, Queue):
        if not cast_type.is_specified():
            return Tuple[dtype[0], dtype[1:]]

    else:
        return cast_type


class CastTypePlugin(TypingNamespacePlugin):
    @classmethod
    def bind(cls):
        cls.registry['TypeArithNamespace']['cast'] = cast
