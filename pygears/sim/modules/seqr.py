from pygears import GearDone, gear
from pygears.typing import TLM

@gear
async def seqr(*, t, seq) -> TLM['t']:
    for val in seq:
        # print("Sequencer: ", val)
        yield val

    # print(f'Sequence {seq} done')
    raise GearDone
