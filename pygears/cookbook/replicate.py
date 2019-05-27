from pygears import gear
from pygears.util.utils import qrange
from pygears.typing import Queue, Tuple, Uint


@gear(svgen={'compile': True, 'inline_conditions': True})
async def replicate(din: Tuple[{
        'length': Uint['w_len'],
        'value': 'w_val'
}]) -> Queue['w_val']:
    """Replicates the input data. The ``length`` field of the :class:`Tuple`
    input type specifies the number of times the ``value`` field needs to be
    reproduced.

    Returns:
        A :class:`Queue` type where each element is equal to the ``value`` input
          field and the `eot` signalizes the last replicated element.
    """
    i = din.dtype[0](0)

    async with din as (length, value):
        for i, last in qrange(length):
            yield (value, last)
