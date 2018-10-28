from pygears import alternative, gear
from pygears.typing import Queue, Uint


@gear
async def take(din: Queue['T'], cfg: Uint['N']) -> b'Queue[T]':

    cnt = 0
    val = din.dtype((0, 0))

    async with cfg as c:
        while not val.eot:
            async with din as val:
                cnt += 1
                if cnt <= c:
                    yield din.dtype((val.data, val.eot or (cnt == c)))


@alternative(take)
@gear(svgen={'svmod_fn': 'qtake.sv'})
async def qtake(din: Queue['Tdin', 2], cfg: Uint['N']) -> Queue['Tdin', 2]:
    '''
    Takes given number of queues. Number given by cfg.
    Counts lower eot. Higher eot resets.
    '''

    cnt = 0
    val = din.dtype((0, 0))

    async with cfg as c:
        while not all(val.eot):
            async with din as val:
                if cnt <= c:
                    yield din.dtype((val.data, val.eot[0], val.eot[1]
                                     or (cnt == (c - 1))))
                cnt += val.eot[0]
