from pygears import alternative, gear
from pygears.lib import cart
from pygears.typing import Bool, Queue, Tuple, Uint


@gear
async def take(din: Queue[Tuple[{
        'data': 't_data',
        'size': Uint
}], 't_lvl'],
               *,
               init=1) -> Queue['t_data', 't_lvl']:
    """Takes the requested number of input data. The rest are consumed. The
    ``data`` field of the :class:`Tuple` type is passed to output, while the
    ``size`` field specifies the requested count. The module resets when the
    input transaction is finished.

    Args: init: Initialization value for the counter

    Returns: A :class:`Queue` type whose data consists of the input ``data``
        field of the :class:`Tuple`. """

    cnt = din.dtype.data['size'](init)
    last_take: Bool

    async for ((data, size), eot) in din:
        last_take = (cnt == size)

        if (cnt <= size):
            yield (data, eot | (last_take << (din.dtype.lvl - 1)))

        if all(eot[:(din.dtype.lvl - 1)]):
            cnt += 1


@alternative(take)
@gear
def take2(din: Queue, size: Uint):
    return cart(size, din, order=[1, 0]) | take
