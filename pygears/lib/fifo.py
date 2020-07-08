from pygears import gear, module, GearDone, Intf, alternative
from pygears.sim import delta, clk
from pygears.typing import Unit, Bool


@gear
async def fifo(din, *, depth=2, threshold=0, regout=False) -> b'din':
    '''For this implementation depth must be a power of 2'''

    data = []
    out_data = False
    dout = module().dout

    while (1):
        if len(data) <= threshold and din.done:
            raise GearDone

        # TODO: Make fifo work correctly in corner case when it is full, but
        # consumer is ready
        if len(data) < depth:
            if not din.empty():
                data.insert(0, din.get_nb())

        if len(data) > threshold and not out_data and dout.ready_nb():
            dout.put_nb(data[-1])
            out_data = True

        await delta()

        if out_data and dout.ready_nb():
            data.pop()
            out_data = False

        await clk()
