import random

from pygears import gear
from pygears.core.util import perpetum
from pygears.sim import clk


@gear
async def delay_gen(din, *, f) -> b'din':
    """Delays the data by waiting a given number of clock cycles

    Args:
        f: iterable which specifies the delay values
    """
    async with din as item:
        try:
            for i in range(next(f)):
                await clk()
        except StopIteration:
            pass

        yield item


def delay(cycles):
    return delay_gen(f=perpetum(lambda x: x, cycles))


def delay_rng(start, stop):
    """Delays each input data for a random number of clock cycles which is chosen
    from a (start, stop) range.
    """
    return delay_gen(f=perpetum(random.randint, start, stop))
