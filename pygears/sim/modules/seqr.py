from pygears import StopGear, gear
from pygears.sim.scv import SCVTypeSeqVisitor, scv_compile
from pygears.sim import cur_gear, artifacts_dir
from pygears.typing import TLM
import os


@gear
async def seqr(*, t, seq) -> TLM['t']:
    for val in seq:
        print(val)
        yield val

    raise StopGear
