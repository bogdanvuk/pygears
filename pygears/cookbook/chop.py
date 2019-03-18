from pygears import alternative, gear
from pygears.common import cart
from pygears.typing import Queue, Tuple, Uint


@gear(svgen={'compile': True})
async def chop(din: Queue[Tuple[{
        'data': 't_data',
        'size': Uint
}]], *, init=1) -> Queue['t_data', 2]:
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

    async for ((data, size), eot) in din:
        last = (cnt == size)

        out_eot = eot @ (eot or last)
        yield (data, out_eot)

        if last:
            cnt = init
        else:
            cnt += 1


@alternative(chop)
@gear
def chop2(din: Queue['t_data'], cfg: Uint):
    return cart(din, cfg) | chop
