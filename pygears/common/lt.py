from pygears.conf import safe_bind
from pygears.core.gear import gear
from pygears.core.intf import IntfOperPlugin
from pygears.typing import Uint


@gear
def lt(*din,
       din0_signed=b'typeof(din0, Int)',
       din1_signed=b'typeof(din1, Int)') -> Uint[1]:
    pass


class MulIntfOperPlugin(IntfOperPlugin):
    @classmethod
    def bind(cls):
        safe_bind('gear/intf_oper/__lt__', lt)
