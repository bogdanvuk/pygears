from pygears import alternative, gear
from pygears.conf import safe_bind
from pygears.core.intf import IntfOperPlugin
from pygears.typing import Integer, Tuple
from pygears.util.hof import oper_tree
from . import ccat


@gear(svgen={'compile': True})
async def add(din: Tuple[Integer['N1'], Integer['N2']]) -> b'din[0] + din[1]':
    async with din as data:
        yield data[0] + data[1]


@alternative(add)
@gear
def add2(din0: Integer, din1: Integer):
    return ccat(din0, din1) | add


@alternative(add)
@gear
def add_vararg(*din: Integer, enablement=b'len(din) > 2'):
    return oper_tree(din, add)


class AddIntfOperPlugin(IntfOperPlugin):
    @classmethod
    def bind(cls):
        safe_bind('gear/intf_oper/__add__', add)
