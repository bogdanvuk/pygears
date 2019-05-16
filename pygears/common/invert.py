from pygears.conf import safe_bind
from pygears import gear
from pygears.core.intf import IntfOperPlugin


@gear(hdl={'compile': True})
async def invert(din) -> b'din':
    async with din as data:
        yield ~data


class InvertIntfOperPlugin(IntfOperPlugin):
    @classmethod
    def bind(cls):
        safe_bind('gear/intf_oper/__invert__', invert)
