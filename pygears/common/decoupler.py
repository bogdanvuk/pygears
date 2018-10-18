import asyncio

from pygears import gear, module, GearDone, registry
from pygears.util.find import find
from pygears.sim import delta, clk, sim_log


def decoupler_din_setup(module):
    module.queue = asyncio.Queue(maxsize=module.params['depth'])


@gear(sim_setup=decoupler_din_setup, svgen={'node_cls': None})
async def decoupler_din(din: 'tdin', *, depth) -> None:
    async with din as d:
        await module().queue.put(d)
        while (module().queue.full()):
            await delta()


def decoupler_dout_setup(module):
    module.decoupler_din = find('../decoupler_din')


@gear(sim_setup=decoupler_dout_setup, svgen={'node_cls': None})
async def decoupler_dout(*, t, depth) -> b't':
    queue = module().decoupler_din.queue
    while queue.empty():
        if registry('sim/map')[module().decoupler_din].done:
            raise GearDone

        await clk()

    yield queue.get_nowait()

    queue.task_done()
    await clk()


@gear
def decoupler(din: 'tdin', *, depth=2) -> b'tdin':
    din | decoupler_din(depth=depth)
    return decoupler_dout(t=din.dtype, depth=depth)


buff = decoupler(depth=1)
