from pygears import gear, IntfEmpty
from pygears.typing import Uint, Bool
from pygears.sim import clk


@gear
async def rom(addr: Uint, *, data, dtype, dflt=None) -> b'dtype':
    a = addr.dtype()
    valid = Bool(False)

    while True:
        if valid:
            if dflt is None:
                d = data[int(a)]
            else:
                try:
                    d = data[int(a)]
                except (IndexError, KeyError):
                    d = dflt
            yield d

            try:
                a = addr.get_nb()
                valid = True
            except IntfEmpty:
                valid = False
        else:
            a = await addr.get()
            valid = True
            await clk()
