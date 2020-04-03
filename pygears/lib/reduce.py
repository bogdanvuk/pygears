from pygears import alternative, gear
from pygears.lib import cart
from pygears.typing import Any, Bool, Queue, Tuple, Number, code, cast
from pygears.typing import saturate as sat


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
def accum(din: Queue[Tuple[{
        'data': Number,
        'init': Number
}]],
          *,
          t,
          saturate=False) -> b't':
    if saturate:
        return reduce(din, f=lambda x, y: sat(x + y, t), t=t)
    else:
        return reduce(din, f=lambda x, y: x + y, t=t)


@gear
def accum(din: Queue[Number], init: Number, *, saturate=False) -> b't':
    # def add(x, y):

    return reduce(saturate=saturate)
