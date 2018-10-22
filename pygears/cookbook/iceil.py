from pygears.typing import Uint
from pygears import gear


@gear(svgen={'svmod_fn': 'iceil.sv'})
async def iceil(din: Uint['T'], *, div=4) -> Uint['T']:
    async with din as val:
        yield (val + div - 1) // div
