from pygears import gear
from pygears.typing import Uint
from pygears.sim import log


@gear
async def unary(din: Uint['w_data']) -> Uint['2**(int(w_data)-1)']:
    '''Returns the unary representation of a binary number'''
    async with din as val:
        if val > 2**(din.dtype.width - 1):
            log.error(
                f'{val} supplied, but only numbers <= {2**(din.dtype.width-1)} supported for this instance'
            )

        if val == 0:
            yield 0
        else:
            yield int('1' * int(val), 2)
