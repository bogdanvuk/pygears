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
    try:
        async with din as d:
            await module().queue.put(d)
            while (module().queue.full()):
                await delta()
    except GearDone:
        if module().queue.empty():
            await module().queue.put(None)

        raise GearDone


def decouple_dout_setup(module):
    module.decouple_din = find('../decouple_din')


@gear(sim_setup=decouple_dout_setup)
async def decouple_dout(*, t, depth) -> b't':

    din = module().decouple_din
    if din.queue.empty() and (din not in reg['sim/map'] or reg['sim/map'][din].done):
        raise GearDone

    queue = din.queue
    data = await queue.get()

    yield data

    queue.task_done()
    await clk()


def check_depth_pow2(depth):
    import math
    # Used to specify infinite depth size
    if depth == 0:
        return True

    from pygears.typing import TypeMatchError
    if int(math.log(depth, 2)) != math.log(depth, 2):
        raise TypeMatchError(f"Decoupler depth needs to be a power of 2, got '{depth}'")

    return True

@gear(hdl={'hierarchical': False}, enablement=b'check_depth_pow2(depth)')
def decouple(din, *, depth=2, init=None) -> b'din':
    din | decouple_din(depth=depth, init=init)
    return decouple_dout(t=din.dtype, depth=depth)


buff = decouple(depth=1)
