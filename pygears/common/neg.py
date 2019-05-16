from pygears import module
from pygears.conf import safe_bind
from pygears import gear
from pygears.core.intf import IntfOperPlugin
from pygears.typing import Int, Integer


def neg_type(dtype):
    return Int[int(dtype)]


@gear(hdl={'hdl_fn': 'neg'})
async def neg(din: Integer) -> b'neg_type(din)':
    async with din as d:
        yield module().tout(-d)


class NegIntfOperPlugin(IntfOperPlugin):
    @classmethod
    def bind(cls):
        safe_bind('gear/intf_oper/__neg__', neg)
