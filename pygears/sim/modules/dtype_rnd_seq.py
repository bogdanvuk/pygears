from pygears import gear, StopGear, registry
from pygears.sim.scv import SCVTypeSeqVisitor, scv_compile, create_type_cons
from pygears.sim import cur_gear, artifacts_dir
from pygears.typing import TLM
import tempfile
import os


@gear
async def dtype_rnd_seq(*, t, outdir=None, cons=None) -> TLM['t']:
    if cons is None:
        cons = create_type_cons(t)

    if not outdir:
        outdir = os.path.join(
                artifacts_dir(),
                cur_gear().basename)

    scvlib = scv_compile(outdir, cur_gear().basename, cons)
    scvlib.randomize_seed()

    yield SCVTypeSeqVisitor(scvlib).visit(t)

    raise StopGear
