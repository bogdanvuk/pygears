from pygears import alternative, gear
from pygears.lib import cart
from pygears.typing import Queue, Uint, Tuple, Bool


@gear
async def clip(din: Queue[Tuple[{
        'data': 't_data',
        'size': Uint
}]], *, init=1) -> Queue['t_data']:
    """Clips the input transaction into two separate transactions by
    sending the ``eot`` after a given number of data has passed (specified by
    the ``size`` field of the :class:`Tuple`)

    Args:
        init: Initialization value for the counter

    Returns:
        A :class:`Queue` type whose data consists of the ``data`` field of
          the :class:`Tuple` input
    """
    cnt = din.dtype.data['size'](init)
    pass_eot = Bool(True)

    async for ((data, size), eot) in din:
        yield (data, eot or ((cnt == size) and pass_eot))

        if ((cnt == size) and pass_eot):
            # to prevent wraparound if counter overflows
            pass_eot = 0
        cnt += 1


@alternative(clip)
@gear
def clip2(din: Queue, size: Uint, *, init=1) -> b'din':
    return cart(size, din, order=[1, 0]) | clip(init=init)
