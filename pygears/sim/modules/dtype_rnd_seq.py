from pygears.sim.scv import SCVTypeSeqVisitor, scv_compile
from pygears.sim import artifacts_dir
from pygears import module
import os


def dtype_rnd_seq(t, outdir=None, cons=None):
    if cons is not None:
        if not outdir:
            outdir = os.path.join(artifacts_dir(), module().basename)

        scvlib = scv_compile(outdir, module().basename, cons)
        scvlib.randomize_seed()
    else:
        scvlib = None

    yield SCVTypeSeqVisitor(scvlib).visit(t)
