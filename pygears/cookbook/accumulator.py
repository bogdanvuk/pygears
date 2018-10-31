from pygears import gear
from pygears.typing import Queue, Tuple, Integer


@gear
async def accumulator(din: Queue[Tuple[Integer['w_data'], Integer['w_data']]]
                      ) -> b'din[0][0]':

    val = din.dtype(((0, 0), 0))
    acc = 0

    while not val.eot:
        async with din as val:
            data, offset = val.data
            acc += data

    yield acc + offset
