from pygears.conf import safe_bind
from pygears import gear
from pygears.core.intf import IntfOperPlugin
from pygears.typing import Number, Tuple


@gear(hdl={'compile': True})
async def div(din: Tuple[{
        'a': Number['N1'],
        'b': Number['N2']
}]) -> b'din[0] // din[1]':
    async with din as data:
        yield data[0] // data[1]


class MulIntfOperPlugin(IntfOperPlugin):
    @classmethod
    def bind(cls):
        safe_bind('gear/intf_oper/__floordiv__', div)
