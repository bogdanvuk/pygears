from pygears.common.serialize import serialize, TDin
from pygears.cookbook.verif import directed, verif
from pygears.sim import sim
from pygears.sim.modules.drv import drv
from pygears.typing import Array, Uint


def test_directed(tmpdir, sim_cls):
    brick_size = 4
    seq_list = [1, 2, 3, 4]

    directed(
        drv(t=Array[Uint[16], brick_size],
            seq=[(i, ) * brick_size for i in seq_list]),
        f=serialize(sim_cls=sim_cls),
        ref=sorted(seq_list * brick_size))

    sim(outdir=tmpdir)


def test_directed_active(tmpdir, sim_cls):
    no = 4
    directed(
        drv(t=TDin[16, no, 4], seq=[((3, ) * no, 3)]),
        f=serialize(sim_cls=sim_cls),
        ref=[[3, 3, 3]])

    sim(outdir=tmpdir)


def test_cosim(tmpdir, sim_cls):
    brick_size = 4
    seq_list = [1, 2, 3, 4]
    verif(
        drv(t=Array[Uint[16], brick_size],
            seq=[(i, ) * brick_size for i in seq_list]),
        f=serialize(sim_cls=sim_cls),
        ref=serialize(name='ref_model'))

    sim(outdir=tmpdir)
