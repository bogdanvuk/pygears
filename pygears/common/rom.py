from pygears import gear
from pygears.typing import Uint


@gear
async def rom(addr: Uint, *, data, dtype, dflt=0) -> b'dtype':
    pass
