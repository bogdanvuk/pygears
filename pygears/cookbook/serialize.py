from pygears import gear
from pygears.typing import Array


@gear
async def serialize(din: Array['data_t', 'brick_size']) -> b'data_t':
    async with din as val:
        for i in range(len(val)):
            yield val[i]
