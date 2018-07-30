from pygears import gear
from pygears.typing import Array


@gear
async def serialize(din: Array) -> b'din.dtype':
    async with din as val:
        for i in range(len(val)):
            yield val[i]
