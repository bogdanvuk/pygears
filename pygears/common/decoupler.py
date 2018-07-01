import asyncio

from pygears import gear, module
from pygears.util.find import find
from pygears.sim import clk

def decoupler_din_setup(module):
    module.queue = asyncio.Queue(maxsize=module.params['depth'])


@gear(sim_setup=decoupler_din_setup)
async def decoupler_din(din: 'tdin', *, depth) -> None:
    async with din as d:
        # while len(queue) == depth:
        #     await clk()
        print(f'{module().name} put {d}')
        await module().queue.put(d)
        print(f'{module().name} put ack')


@gear
async def decoupler_dout(*, t, depth) -> b't':
    # while not queue:
    #     await clk()

    queue = find('../decoupler_din').queue

    print(f'{module().name} waiting for input')
    data = await queue.get()
    print(f'{module().name} put {data}')
    yield data
    print(f'{module().name} put ack')
    queue.task_done()


@gear
def decoupler(din: 'tdin', *, depth=2) -> b'tdin':
    din | decoupler_din(depth=depth)
    return decoupler_dout(t=din.dtype, depth=depth)
