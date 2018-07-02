from pygears.core.gear import gear
from pygears.typing import Integer, Int
from pygears.core.intf import IntfOperPlugin
from pygears import module


def neg_type(dtype):
    return Int[int(dtype)]


@gear(svgen={'svmod_fn': 'neg.sv'})
async def neg(din: Integer) -> b'neg_type(din)':

    async with din as d:
        yield module().tout(-d)


class NegIntfOperPlugin(IntfOperPlugin):
    @classmethod
    def bind(cls):
        cls.registry['IntfOperNamespace']['__neg__'] = neg
