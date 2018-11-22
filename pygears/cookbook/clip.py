from pygears import alternative, gear
from pygears.common import cart
from pygears.typing import Queue, Uint, Tuple


@gear(svgen={'compile': True})
async def clip(din: Queue[Tuple['t_data', Uint]], *,
               init=1) -> Queue['t_data']:
    ''' Clips the input transaction into two separate transactions by
sending eot after a given number of data has passed (specified by
configuration). The second eot is passed from input.
    '''
    cnt = din.dtype[0][1](init)
    pass_eot = Uint[1](1)

    async for ((data, size), eot) in din:
        yield (data, eot or ((cnt == size) and pass_eot))
        if ((cnt == size) and pass_eot):
            # to prevent wraparound if counter overflows
            pass_eot = 0
        cnt += 1


@alternative(clip)
@gear
def clip2(din: Queue['t_data'], cfg: Uint):
    return cart(din, cfg) | clip
