from pygears import gear
from pygears.typing import Queue, Tuple, Integer


@gear(svgen={'compile': True})
async def accumulator(din: Queue[Tuple[Integer['w_data'], Integer['w_data']]]
                      ) -> b'din[0][0]':

    acc = din.dtype[0][0](0)
    offset_added = False

    async for ((data, offset), eot) in din:
        if offset_added:
            acc = acc + int(data)
        else:
            acc = offset + int(data)
            offset_added = True

    yield acc
