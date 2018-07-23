from pygears import gear
from pygears.sim import clk
from pygears.core.util import perpetum
import random


@gear
async def delay(din, *, f) -> b'din':
    async with din as item:
        for i in range(next(f)):
            await clk()

        yield item


def delay_rng(start, stop):
    return delay(f=perpetum(random.randint, start, stop))
