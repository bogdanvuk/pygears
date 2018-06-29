from pygears import gear
from pygears.sim import cur_gear, clk


@gear
async def decoupler_din(din: 'tdin', *, queue, depth) -> None:
    async with din as d:
        while len(queue) == depth:
            await clk()

        queue.insert(0, d)


@gear
async def decoupler_dout(*, t, queue, depth) -> b't':
    while not queue:
        await clk()

    yield queue.pop()


@gear
def decoupler(din: 'tdin', *, depth=2) -> b'tdin':

    queue = []
    din | decoupler_din(queue=queue, depth=depth)
    return decoupler_dout(t=din.dtype, queue=queue, depth=depth)
