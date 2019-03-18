from pygears import gear
from pygears.typing import Uint


@gear(svgen={'compile': True})
async def iceil(din: Uint['T'], *, div=4) -> Uint['T']:
    """Performs division of the input value and return the ceiling of the
    calculated value

    Args:
        div: The divisor value
    """
    async with din as val:
        yield (val + div - 1) // div
