from pygears.conf import safe_bind
from pygears import alternative, gear
from pygears.typing import Integer, Tuple
from pygears.core.intf import IntfOperPlugin
from pygears.util.hof import oper_reduce
from . import ccat


@gear(svgen={'compile': True})
async def sub(din: Tuple[Integer['N1'], Integer['N2']]) -> b'din[0] - din[1]':
    async with din as data:
        yield data[0] - data[1]


@alternative(sub)
@gear
def sub2(din0: Integer, din1: Integer):
    return ccat(din0, din1) | sub


@alternative(sub)
@gear(enablement=b'len(din) > 2')
def sub_vararg(*din: Integer):
    return oper_reduce(din, sub)


class SubIntfOperPlugin(IntfOperPlugin):
    @classmethod
    def bind(cls):
        safe_bind('gear/intf_oper/__sub__', sub)
