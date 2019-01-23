from pygears import alternative, gear
from pygears.common import cart
from pygears.typing import Queue, Tuple, Uint


@gear(svgen={'compile': True})
async def take(din: Queue[Tuple['t_data', Uint]], *,
               init=1) -> Queue['t_data']:

    cnt = din.dtype[0][1](init)
    pass_eot = True

    async for ((data, size), eot) in din:
        last = (cnt == size) and pass_eot
        if (cnt <= size) and pass_eot:
            yield (data, eot or last)
        if last:
            pass_eot = 0
        cnt += 1


@alternative(take)
@gear
def take2(din: Queue['t_data'], cfg: Uint):
    return cart(din, cfg) | take


@alternative(take)
@gear(svgen={'compile': True})
async def qtake(din: Queue[Tuple['t_data', Uint], 2], *,
                init=0) -> Queue['t_data', 2]:
    '''
    Takes given number of queues. Number given by cfg.
    Counts lower eot. Higher eot resets.
    '''

    cnt = din.dtype[0][1](init)
    pass_eot = True

    async for ((data, size), eot) in din:
        cnt += eot[0]
        last = (cnt == size) and pass_eot
        if (cnt <= size) and pass_eot:
            yield (data, eot | (last << 1))
        if last:
            pass_eot = 0


@alternative(take)
@gear
def qtake2(din: Queue['t_data', 2], cfg: Uint):
    return cart(din, cfg) | take
