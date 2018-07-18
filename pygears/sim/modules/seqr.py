from pygears import GearDone, gear
from pygears.typing import TLM


@gear
async def seqr(*, t, seq) -> TLM['t']:
    for val in seq:
        yield val

    raise GearDone


@gear
async def delay_seqr(din: TLM['t'], *, seq) -> TLM['t']:
    item = await din.get()
    for val in seq:
        yield val

    # raise GearDone
