from pygears.core.gear import gear
from pygears.util.utils import gather


@gear
async def ccat(*din) -> b'Tuple[din]':
    async with gather(*din) as dout:
        yield dout
