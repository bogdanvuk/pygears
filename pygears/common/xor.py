from pygears import alternative, gear

from pygears.conf import safe_bind
from pygears.core.intf import IntfOperPlugin
from pygears.typing import Any, Tuple
from . import ccat


@gear(hdl={'compile': True})
async def xor(din: Tuple[Any, Any]) -> b'din[0]':
    async with din as data:
        yield data[0] ^ data[1]


@alternative(xor)
@gear
def xor2(din0: Any, din1: Any):
    return ccat(din0, din1) | xor


class MulIntfOperPlugin(IntfOperPlugin):
    @classmethod
    def bind(cls):
        safe_bind('gear/intf_oper/__xor__', xor)
