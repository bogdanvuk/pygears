from pygears.core.gear import gear
from pygears.typing import Uint
from pygears.core.intf import IntfOperPlugin


@gear
def lt(*din,
       din0_signed=b'typeof(din0, Int)',
       din1_signed=b'typeof(din1, Int)') -> Uint[1]:
    pass


class MulIntfOperPlugin(IntfOperPlugin):
    @classmethod
    def bind(cls):
        cls.registry['IntfOperNamespace']['__lt__'] = lt
