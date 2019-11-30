from pygears import gear
from pygears.typing import saturate as type_saturate


@gear
async def saturate(din, *, t, limits=None) -> b't':
    async with din as d:
        yield type_saturate(d, t, limits=limits)
