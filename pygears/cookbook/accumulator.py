from pygears import alternative, gear
from pygears.common import cart
from pygears.typing import Queue, Tuple, Integer, Bool


@gear(svgen={'compile': True})
async def accumulator(din: Queue[Tuple[{
        'data': Integer['w_data'],
        'offset': Integer['w_data']
}]]) -> b'din.data["data"]':

    acc = din.dtype.data['data'](0)
    offset_added = Bool(False)

    async for ((data, offset), eot) in din:
        if offset_added:
            acc = acc + int(data)
        else:
            acc = offset + int(data)
            offset_added = True

    yield acc


@alternative(accumulator)
@gear
def accumulator2(din: Queue[Integer['w_data']], cfg: Integer['w_data']):
    return cart(din, cfg) | accumulator
