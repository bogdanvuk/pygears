from pygears import alternative, gear
from pygears.conf import safe_bind
from pygears.core.intf import IntfOperPlugin
from pygears.typing import Integer, Tuple, Number
from pygears.util.hof import oper_tree


@gear(hdl={'compile': True})
async def add(din: Tuple[Number, Number]) -> b'din[0] + din[1]':
    async with din as data:
        yield data[0] + data[1]


@alternative(add)
@gear(enablement=b'len(din) > 2')
def add_vararg(*din: Integer):
    return oper_tree(din, add)


class AddIntfOperPlugin(IntfOperPlugin):
    @classmethod
    def bind(cls):
        safe_bind('gear/intf_oper/__add__', add)
