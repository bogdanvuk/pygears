from pygears import alternative, gear
from pygears.common import cart
from pygears.typing import Bool, Queue, Tuple, Uint


@gear(hdl={'compile': True})
async def take(din: Queue[Tuple[{
        'data': 't_data',
        'size': Uint
}]], *, init=1) -> Queue['t_data']:
    """Takes the requested number of input data. The rest are consumed.
    The ``data`` field of the :class:`Tuple` type is passed to output, while the
    ``size`` field specifies the requested count. The module resets when the
    input transaction is finished.

    Args:
        init: Initialization value for the counter

    Returns:
        A :class:`Queue` type whose data consists of the input ``data`` field of
          the :class:`Tuple`.
    """
    cnt = din.dtype[0][1](init)
    pass_eot = Bool(True)

    async for ((data, size), eot) in din:
        last = (cnt == size) and pass_eot
        if (cnt <= size) and pass_eot:
            yield (data, eot or last)
        if last:
            pass_eot = 0
        cnt += 1


@alternative(take)
@gear
def take2(din: Queue['t_data'], cfg: Uint):
    return cart(din, cfg) | take


@alternative(take)
@gear(hdl={'compile': True})
async def qtake(din: Queue[Tuple[{
        'data': 't_data',
        'size': Uint
}], 2],
                *,
                init=0) -> Queue['t_data', 2]:
    """Alternative to the take module where the ``size`` filed of
    the :class:`Tuple` specifies the number of transactions.
    """

    cnt = din.dtype[0][1](init)
    pass_eot = Bool(True)

    async for ((data, size), eot) in din:
        cnt += eot[0]
        last = (cnt == size) and pass_eot
        if (cnt <= size) and pass_eot:
            yield (data, eot | (last << 1))
        if last:
            pass_eot = 0


@alternative(take)
@gear
def qtake2(din: Queue['t_data', 2], cfg: Uint):
    return cart(din, cfg) | take
