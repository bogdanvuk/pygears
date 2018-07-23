import asyncio

from pygears import gear, module, GearDone
from pygears.util.find import find
from pygears.sim import sim_log, delta


def decoupler_din_setup(module):
    module.queue = asyncio.Queue(maxsize=module.params['depth'])


@gear(sim_setup=decoupler_din_setup, svgen={'node_cls': None})
async def decoupler_din(din: 'tdin', *, depth) -> None:
    try:
        async with din as d:
            await module().queue.put(d)
            sim_log().info(f'qsize: {module().queue.qsize()}')
            while (module().queue.full()):
                await delta()

            sim_log().info(f'allowed')

    except GearDone:
        # await module().queue.join()
        await module().queue.put(GearDone)
        raise GearDone


def decoupler_dout_setup(module):
    module.decoupler_din = find('../decoupler_din')


@gear(sim_setup=decoupler_dout_setup, svgen={'node_cls': None})
async def decoupler_dout(*, t, depth) -> b't':
    queue = module().decoupler_din.queue
    data = await queue.get()
    sim_log().info(f'data: {data}, qsize: {queue.qsize()}')

    if data is GearDone:
        queue.task_done()
        raise GearDone

    yield data
    queue.task_done()


@gear
def decoupler(din: 'tdin', *, depth=2) -> b'tdin':
    din | decoupler_din(depth=depth)
    return decoupler_dout(t=din.dtype, depth=depth)


buff = decoupler(depth=1)
