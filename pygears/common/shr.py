from pygears import gear
from pygears.typing import Integer, Uint
from pygears.core.intf import IntfOperPlugin


@gear
def shr(din: Integer, cfg: Uint['w_shamt'], *,
        signed=b'typeof(din, Int)') -> b'din':
    pass


class MulIntfOperPlugin(IntfOperPlugin):
    @classmethod
    def bind(cls):
        cls.registry['IntfOperNamespace']['__rshift__'] = shr
