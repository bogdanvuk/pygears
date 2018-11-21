from pygears import gear, module
from pygears.conf import gear_log
from pygears.typing import Queue, Uint


@gear
async def clip(din: Queue['T'], cfg: Uint) -> Queue['T']:
    ''' Clips the input transaction into two separate transactions by
sending eot after a given number of data has passed (specified by
configuration). The second eot is passed from input.
    '''
    i = 0
    val = din.dtype((0, 0))

    async with cfg as size:
        while (val.eot == 0):
            i += 1
            async with din as val:
                eot = val.eot or (i == size)
                dout = module().tout((val.data, eot))
                gear_log().debug(f'Clip yielding {dout}')
                yield dout
