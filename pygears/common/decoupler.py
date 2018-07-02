import asyncio

from pygears import gear, module
from pygears.util.find import find


def decoupler_din_setup(module):
    module.queue = asyncio.Queue(maxsize=module.params['depth'])


@gear(sim_setup=decoupler_din_setup)
async def decoupler_din(din: 'tdin', *, depth) -> None:
    async with din as d:
        await module().queue.put(d)


@gear
async def decoupler_dout(*, t, depth) -> b't':
    queue = find('../decoupler_din').queue
    data = await queue.get()
    yield data
    queue.task_done()


@gear
def decoupler(din: 'tdin', *, depth=2) -> b'tdin':
    din | decoupler_din(depth=depth)
    return decoupler_dout(t=din.dtype, depth=depth)
