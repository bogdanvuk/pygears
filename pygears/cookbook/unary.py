from pygears import gear, module
from pygears.typing import Uint


@gear
async def unary(din: Uint['w_data']) -> Uint['2**(int(w_data))']:
    '''Returns the unary representation of a binary number'''
    async with din as val:
        yield module().tout(int('1' * val, 2))
