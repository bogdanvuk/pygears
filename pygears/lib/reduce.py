from pygears import gear
from pygears.typing import Number, Queue, saturate


@gear(hdl={'compile': True})
async def reduce(din: Queue, init, *, f) -> b'init':
    acc: init.dtype = None

    async with init as i:
        acc = i
        async for (d, eot) in din:
            acc = f(acc, d)

            if eot:
                yield acc


@gear
def accum(din: Queue[Number], init: Number, *, cast=saturate) -> b'init':
    def add(x, y):
        return cast(x + y, t=init.dtype)

    return reduce(din, init, f=add)
