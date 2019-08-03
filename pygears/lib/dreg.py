from pygears import gear, QueueEmpty
from pygears.typing import Bool
from pygears.sim import clk


@gear
async def dreg(din) -> b'din':
    data = din.dtype.decode(0)
    valid = Bool(False)

    while True:
        if valid:
            yield data

            try:
                data = din.get_nb()
                valid = True
            except QueueEmpty:
                valid = False
        else:
            data = await din.get()
            valid = True
            await clk()
