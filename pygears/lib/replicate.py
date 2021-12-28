from pygears import gear
from pygears.util.utils import qrange
from pygears.typing import Queue, Tuple, Uint, Any, Bool, typeof


@gear
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
        for i, last in qrange(length):
            yield (value, last)


@gear
async def replicate_while(cond: Bool, data: Any) -> Queue['data']:
    async with data as d:
        last = False
        while not last:
            async with cond as en:
                last = not en
                if typeof(data.dtype, Queue):
                    yield (d[0], d[1] @ last)
                else:
                    yield (d, last)


@gear
def replicate_until(cond: Bool, data: Any):
    return replicate_while(~cond, data)
