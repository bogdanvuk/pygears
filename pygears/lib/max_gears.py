from pygears import alternative, gear
from pygears.lib import ccat
from pygears.typing import Integer, Tuple


@gear
async def max2(
        din: Tuple[Integer['N1'], Integer['N2']]) -> b'max(din[0], din[1])':
    """Finds the highest of the two values"""
    async with din as data:
        yield max(data)


@alternative(max2)
@gear
def max22(din0: Integer, din1: Integer):
    return ccat(din0, din1) | max2
