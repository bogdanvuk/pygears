import asyncio

from pygears import gear, module, GearDone, reg
from pygears.util.find import find
from pygears.sim import delta, clk


def decouple_din_setup(module):
    module.queue = asyncio.Queue(maxsize=module.params['depth'])
    if module.params['init'] is not None:
        module.queue.put_nowait(module.params['init'])


@gear(sim_setup=decouple_din_setup)
async def decouple_din(din, *, depth, init) -> None:
    async with din as d:
        await module().queue.put(d)
        while (module().queue.full()):
            await delta()


def decouple_dout_setup(module):
    module.decouple_din = find('../decouple_din')


@gear(sim_setup=decouple_dout_setup)
async def decouple_dout(*, t, depth) -> b't':
    queue = module().decouple_din.queue
    while queue.empty():
        if reg['sim/map'][module().decouple_din].done:
            raise GearDone

        await clk()

    yield queue.get_nowait()

    queue.task_done()
    await clk()


@gear(hdl={'hierarchical': False})
def decouple(din, *, depth=2, init=None) -> b'din':
    din | decouple_din(depth=depth, init=init)
    return decouple_dout(t=din.dtype, depth=depth)


buff = decouple(depth=1)
