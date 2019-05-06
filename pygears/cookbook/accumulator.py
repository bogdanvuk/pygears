from pygears import QueueEmpty, alternative, gear
from pygears.common import cart
from pygears.typing import Bool, Integer, Queue, Tuple

t_din = Queue[Tuple[{'data': Integer['w_data'], 'offset': Integer['w_data']}]]


@gear(svgen={'compile': True})
async def accumulator(din: t_din) -> b'din.data["data"]':
    """Accumulates i.e. sums up the values from the input. The ``data`` field
    values of the input :class:`Tuple` type are accumulated and an initial offset
    can be added via the ``offset`` field. The accumulated sum is returned when
    the input :class:`Queue` terminates at which point the gear resets.

    Returns:
        The accumulated sum which is the same type as the ``data`` field of the
          input :class:`Tuple` type.
    """
    acc = din.dtype.data['data'](0)
    offset_added = Bool(False)

    async for ((data, offset), eot) in din:
        if offset_added:
            acc = acc + int(data)
        else:
            acc = offset + int(data)
            offset_added = True

    yield acc


@gear(svgen={'compile': True})
async def pipelined_accumulator(din: t_din) -> b'din.data["data"]':
    acc = din.dtype.data['data'](0)
    offset_added = Bool(False)
    done = Bool(False)

    while True:
        if done:
            yield acc

            try:
                data, offset, eot = din.get_nb()
                acc = offset + int(data)
                offset_added = True
                done = eot
            except QueueEmpty:
                offset_added = False
                done = False
                acc = 0
        else:
            async for ((data, offset), eot) in din:
                done = eot
                if offset_added:
                    acc = acc + int(data)
                else:
                    acc = offset + int(data)
                    offset_added = True


@alternative(accumulator)
@gear
def accumulator2(din: Queue[Integer['w_data']], cfg: Integer['w_data']):
    return cart(din, cfg) | accumulator


@alternative(accumulator)
@gear(svgen={'compile': True})
async def accumulator_no_offset(din: Queue[Integer['w_data']]) -> b'din.data':
    acc = din.dtype.data(0)

    async for (data, eot) in din:
        acc += int(data)

    yield acc
