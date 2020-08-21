from pygears import gear
from pygears.core.partial import Partial
from pygears.typing import Number, Queue, saturate


@gear(hdl={'compile': True})
async def reduce(din: Queue, init, *, f) -> b'init':
    acc: init.dtype = None

    async with init as i:
        acc = i
        async for (d, eot) in din:
            if isinstance(f, Partial):
                async with f(acc, d) as fout:
                    acc = fout

                    if eot:
                        yield acc
            else:
                acc = f(acc, d)

                if eot:
                    yield acc


@gear
def accum(din: Queue[Number], init: Number, *, cast=saturate) -> b'init':
    def add(x, y):
        return cast(x + y, t=init.dtype)

    return reduce(din, init, f=add)
