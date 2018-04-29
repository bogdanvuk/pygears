from pygears.core.gear import gear
from pygears.typing.base import TypingMeta
from pygears.core.intf import IntfOperPlugin


@gear
def cast(din, *, cast_type) -> b'cast(din, cast_type)':
    pass


def pipe(self, other):
    if isinstance(other, (str, TypingMeta)):
        if self.producer is not None:
            name = f'cast_{self.producer.basename}'
        else:
            name = 'cast'

        return cast(
            self, cast_type=other, name=name)
    else:
        return other.__ror__(self)


class PipeIntfOperPlugin(IntfOperPlugin):
    @classmethod
    def bind(cls):
        cls.registry['IntfOperNamespace']['__or__'] = pipe
