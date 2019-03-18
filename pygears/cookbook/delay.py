import random

from pygears import gear
from pygears.core.util import perpetum
from pygears.sim import clk


@gear
async def delay(din, *, f) -> b'din':
    """Delays the data by waiting a given number of clock cycles

    Args:
        f: iterable which specifies the delay values
    """
    async with din as item:
        for i in range(next(f)):
            await clk()

        yield item


def delay_rng(start, stop):
    """Delays each input data for a random number of clock cycles which is chosen
    from a (start, stop) range.
    """
    return delay(f=perpetum(random.randint, start, stop))
