from pygears import alternative, gear
from pygears.lib import cart
from pygears.typing import Queue, Tuple, Uint, Bool


@gear
async def chop(din: Queue[Tuple[{
        'data': 't_data',
        'size': Uint
}]], *, init=1) -> Queue['t_data']:
    """Chops the input transaction into sub-transactions by sending the lower
    ``eot`` after a given number of data has passed (specified by the ``size``
    field of the :class:`Tuple`)

    Args:
        init: Initialization value for the counter

    Returns:
        A level 2 :class:`Queue` type whose data consists of the ``data`` field
          of the :class:`Tuple` input
    """

    cnt = din.dtype.data['size'](init)
    last: Bool

    async for ((data, size), eot) in din:
        last = (cnt == size)

        yield (data, eot or last)

        if last:
            cnt = init
        else:
            cnt += 1


@alternative(chop)
@gear
def chop2(din: Queue, size: Uint) -> b'din':
    return cart(size, din, order=[1, 0]) | chop
