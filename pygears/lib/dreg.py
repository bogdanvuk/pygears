from pygears import gear, IntfEmpty
from pygears.typing import Bool
from pygears.sim import clk


@gear
async def dreg(din, *, init=None) -> b'din':
    data = din.dtype() if init is None else din.dtype(init)

    valid = Bool(False) if init is None else Bool(True)

    while True:
        if valid:
            yield data

            try:
                data = din.get_nb()
                valid = True
            except IntfEmpty:
                valid = False
        else:
            data = await din.get()
            valid = True
            await clk()


@gear
def regout(din, *, f):
    return din | f | dreg
