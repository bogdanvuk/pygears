from pygears.core.intf import IntfOperPlugin
from pygears.common import conv
from pygears.typing.base import TypingMeta


def pipe(self, other):
    if isinstance(other, (str, TypingMeta)):
        return conv(
            self, cast_type=other, name=f'conv_{self.producer.basename}')
    else:
        return other.__ror__(self)


class PipeIntfOperPlugin(IntfOperPlugin):
    @classmethod
    def bind(cls):
        cls.registry['IntfOperNamespace']['__or__'] = pipe
