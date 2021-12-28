from pygears import gear
from pygears.sim import clk
from pygears.util.utils import qrange


@gear(enablement='t.data == din')
async def parallelize(din, *, t) -> b't':
    data = t()

    for i, last in qrange(len(t)):
        async with din as val:
            data[i] = val

    await clk()
    yield data
