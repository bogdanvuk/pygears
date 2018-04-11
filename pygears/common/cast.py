from pygears.core.gear import gear
from pygears.typing.base import TypingMeta
from pygears.core.intf import IntfOperPlugin


@gear
def cast(din, *, cast_type) -> 'cast({din}, {cast_type})':
    pass


def pipe(self, other):
    if isinstance(other, (str, TypingMeta)):
        return cast(
            self, cast_type=other, name=f'cast_{self.producer.basename}')
    else:
        return other.__ror__(self)


class PipeIntfOperPlugin(IntfOperPlugin):
    @classmethod
    def bind(cls):
        cls.registry['IntfOperNamespace']['__or__'] = pipe
