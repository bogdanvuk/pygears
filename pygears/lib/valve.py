from pygears import gear
from pygears.typing import Union, Unit


@gear
async def valve(din: Union['Tdin', Unit]) -> b'Tdin':
    async with din as val:
        if not val[-1]:
            yield val[0]
