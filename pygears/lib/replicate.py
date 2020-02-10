from pygears import gear
from .rng import qrange
from pygears.typing import Queue, Tuple, Uint, Any


@gear(hdl={'compile': True})
async def replicate(din: Tuple[{
        'length': Uint,
        'val': Any
}]) -> Queue['din["val"]']:
    """Replicates the input data. The ``length`` field of the :class:`Tuple`
    input type specifies the number of times the ``value`` field needs to be
    reproduced.

    Returns:
        A :class:`Queue` type where each element is equal to the ``value``
           input field and the `eot` signalizes the last replicated element.
    """
    async with din as (length, value):
        async for i, last in qrange(length):
            yield (value, last)
