from pygears import alternative, gear
from pygears.conf import safe_bind
from pygears.core.intf import IntfOperPlugin
from pygears.typing import Integer, Tuple
from pygears.util.hof import oper_reduce
from . import ccat


@gear(svgen={'compile': True, 'inline_conditions': True})
async def mod(din: Tuple[Integer['N1'], Integer['N2']]) -> b'din[0] % din[1]':
    async with din as data:
        yield data[0] % data[1]


@alternative(mod)
@gear
def mod2(din0: Integer, din1: Integer):
    return ccat(din0, din1) | mod


@alternative(mod)
@gear(enablement=b'len(din) > 2')
def mod_vararg(*din: Integer):
    return oper_reduce(din, mod)


class ModIntfOperPlugin(IntfOperPlugin):
    @classmethod
    def bind(cls):
        safe_bind('gear/intf_oper/__mod__', mod)
