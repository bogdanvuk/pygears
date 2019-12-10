from pygears import gear
from pygears.util.utils import qrange


@gear(enablement='t[0] == din')
async def parallelize(din, *, t) -> b't':
    data = [None] * len(t)

    for i, last in qrange(len(t)):
        async with din as val:
            data[i] = val

    yield data
