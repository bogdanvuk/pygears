from pygears import module
from pygears.core.gear import gear
from pygears.conf import gear_log
from pygears.typing import Queue


@gear
async def trr(*din: Queue['t_data']) -> b'Queue[t_data, 2]':
    for i, d in enumerate(din):
        val = din[0].dtype((0, 0))
        while (val.eot == 0):
            async with d as val:
                dout = module().tout((val.data, val.eot, (i == len(din) - 1)))
                gear_log().debug(f'Trr yielding {dout}')
                yield dout
