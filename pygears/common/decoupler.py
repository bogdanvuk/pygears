import asyncio

from pygears import gear, module, GearDone
from pygears.util.find import find


def decoupler_din_setup(module):
    module.queue = asyncio.Queue(maxsize=module.params['depth'])


@gear(sim_setup=decoupler_din_setup, svgen={'node_cls': None})
async def decoupler_din(din: 'tdin', *, depth) -> None:
    try:
        async with din as d:
            await module().queue.put(d)
    except GearDone:
        # await module().queue.put(GearDone)
        raise GearDone


@gear(svgen={'node_cls': None})
async def decoupler_dout(*, t, depth) -> b't':
    queue = find('../decoupler_din').queue
    data = await queue.get()

    if data is GearDone:
        queue.task_done()
        raise GearDone

    yield data
    queue.task_done()


@gear
def decoupler(din: 'tdin', *, depth=2) -> b'tdin':
    din | decoupler_din(depth=depth)
    return decoupler_dout(t=din.dtype, depth=depth)
