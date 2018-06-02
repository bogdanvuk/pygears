from pygears import gear, StopGear
from pygears.sim.scv import SCVTypeSeqVisitor, scv_compile, create_type_cons
from pygears.typing import TLM


@gear
async def dtype_rnd_seq(*, t, outdir, cons=None) -> TLM['t']:
    if cons is None:
        cons = create_type_cons(t)

    scvlib = scv_compile(outdir, 'seq', cons)
    scvlib.randomize_seed()

    yield SCVTypeSeqVisitor(scvlib).visit(t)

    raise StopGear
