from pygears import alternative, gear

from pygears.conf import safe_bind
from pygears.core.intf import IntfOperPlugin
from pygears.typing import Tuple, Any, Uint
from . import ccat


@gear(svgen={'compile': True})
async def eq(din: Tuple[Any, Any]) -> Uint[1]:
    async with din as data:
        yield data[0] == data[1]


@alternative(eq)
@gear
def eq2(din0: Any, din1: Any):
    return ccat(din0, din1) | eq


class MulIntfOperPlugin(IntfOperPlugin):
    @classmethod
    def bind(cls):
        safe_bind('gear/intf_oper/__eq__', eq)
