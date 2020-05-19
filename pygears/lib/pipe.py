from pygears import GearDone, gear, module
from pygears.sim import clk, delta


@gear(hdl={'files': ['dreg']})
async def pipe(din, *, length) -> b'din':
    data = [None] * length
    dout = module().dout

    while True:
        if dout.ready_nb() and data[-1] is not None:
            dout.put_nb(data[-1])

        await delta()

        if dout.ready_nb():
            data[-1] = None

        if all(d is None for d in data) and din.done:
            raise GearDone

        for i in range(length - 1, 0, -1):
            if data[i] is None:
                data[i] = data[i - 1]
                data[i - 1] = None

        if not din.empty() and data[0] is None:
            data[0] = din.get_nb()

        await clk()
