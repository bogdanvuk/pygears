from pygears import alternative, gear
from pygears.conf import safe_bind
from pygears.core.intf import IntfOperPlugin
from pygears.util.hof import oper_tree
from pygears.typing import Integer, Tuple
from . import ccat


@gear(svgen={'compile': True})
async def mul(din: Tuple[Integer['N1'], Integer['N2']]) -> b'din[0] * din[1]':
    async with din as data:
        yield data[0] * data[1]


@alternative(mul)
@gear
def mul2(din0: Integer, din1: Integer):
    return ccat(din0, din1) | mul


@alternative(mul)
@gear(enablement=b'len(din) > 2')
def mul_vararg(*din: Integer):
    return oper_tree(din, mul)


class MulIntfOperPlugin(IntfOperPlugin):
    @classmethod
    def bind(cls):
        safe_bind('gear/intf_oper/__mul__', mul)
