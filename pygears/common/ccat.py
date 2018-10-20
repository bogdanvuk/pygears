from pygears.core.gear import gear
from pygears.util.utils import gather


@gear
async def ccat(*din) -> b'Tuple[din]':
    """Short for concat, combines multiple interfaces into a single interface whose
    type is a :class:`Tuple` of the input interface types. One output data is
    formed by combining one data from each of the inputs::

        din0 = Intf(Uint[8])
        din1 = Intf(Uint[16])

    >>> ccat(din0, din1)
    Intf(Tuple[Uint[8], Uint[16]])

    """

    async with gather(*din) as dout:
        yield dout
