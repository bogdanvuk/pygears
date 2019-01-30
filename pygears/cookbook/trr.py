from pygears.core.gear import gear
from pygears.typing import Queue, Uint, bitw


@gear(svgen={'compile': True})
async def trr(*din: Queue['t_data']) -> b'Queue[t_data, 2]':
    i = Uint[bitw(len(din))](0)

    for i, d in enumerate(din):
        async for (data, eot) in d:
            yield (data, (i == len(din) - 1) @ eot)
