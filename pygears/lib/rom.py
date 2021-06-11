from pygears import gear
from pygears.typing import Uint
from pygears.sim import clk


@gear
async def rom(addr: Uint, *, data, dtype, dflt=None) -> b'dtype':
    async with addr as a:
        if dflt is None:
            d = data[int(a)]
        else:
            try:
                d = data[int(a)]
            except (IndexError, KeyError):
                d = dflt

        await clk()
        yield d
