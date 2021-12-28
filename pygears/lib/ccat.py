from pygears import gear
from pygears.util.utils import gather
from pygears.lib.shred import shred
from pygears.typing import Tuple


# @gear
@gear
async def ccat(*din) -> b'Tuple[din]':
    """Short for concatenate, combines multiple interfaces into a single interface
    whose type is a :class:`Tuple` of the input interface types. One output
    data is formed by combining one data from each of the inputs::

        din0 = Intf(Uint[8])
        din1 = Intf(Uint[16])

    >>> ccat(din0, din1)
    Intf(Tuple[Uint[8], Uint[16]])

    """

    yield [await d.pull() for d in din]

    for d in din:
        d.ack()

    # async with gather(*din) as dout:
    #     yield dout


@gear
def ccat_sync_with(sync_in, din, *, balance=None):
    if balance:
        sync_in = sync_in | balance

    din_sync, sync_in_sync = ccat(din, sync_in)
    sync_in_sync | shred

    return din_sync
