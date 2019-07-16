from pygears import module
from pygears.hls import datagear
from pygears.conf import safe_bind
from pygears.typing import Number
from pygears.core.intf import IntfOperPlugin


@datagear
def shr(din: Number, *, shamt) -> b'din >> shamt':
    return module().tout(din >> shamt)


class MulIntfOperPlugin(IntfOperPlugin):
    @classmethod
    def bind(cls):
        safe_bind('gear/intf_oper/__rshift__', lambda x, y: shr(x, shamt=y))
