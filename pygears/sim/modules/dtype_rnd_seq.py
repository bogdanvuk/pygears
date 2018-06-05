from pygears.sim.scv import SCVTypeSeqVisitor, scv_compile
from pygears.sim import cur_gear, artifacts_dir
import os


def dtype_rnd_seq(t, outdir=None, cons=None):
    if cons is not None:
        if not outdir:
            outdir = os.path.join(artifacts_dir(), cur_gear().basename)

        scvlib = scv_compile(outdir, cur_gear().basename, cons)
        scvlib.randomize_seed()
    else:
        scvlib = None

    yield SCVTypeSeqVisitor(scvlib).visit(t)
