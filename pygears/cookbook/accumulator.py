from pygears import gear
from pygears.typing import Queue, Tuple


@gear
async def accumulator(din: Queue[Tuple['w_data', 'w_data']]) -> b'w_data':

    val = din.dtype(((0, 0), 0))
    acc = 0

    while not val.eot:
        async with din as val:
            data, offset = val.data
            acc += data

    yield acc + offset
