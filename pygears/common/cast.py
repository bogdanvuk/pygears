from pygears.core.gear import Gear, gear
from pygears import Int, Uint, Queue, Tuple
from pygears.typing.base import TypingMeta
from pygears.core.intf import IntfOperPlugin
import types


def type_cast(dtype, cast_type):
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


@gear(gear_cls=Gear, sv_param_kwds=[])
def cast(din, *, cast_type) -> 'cast({din}, {cast_type})':
    pass


def pipe(self, other):
    if isinstance(other, (str, TypingMeta)):
        return cast(
            self, cast_type=other, name=f'cast_{self.producer.basename}')
    else:
        return other.__ror__(self)


typing = types.SimpleNamespace(cast=type_cast)


class PipeIntfOperPlugin(IntfOperPlugin):
    @classmethod
    def bind(cls):
        cls.registry['IntfOperNamespace']['__or__'] = pipe
        cls.registry['TypeArithNamespace']['cast'] = typing.cast
