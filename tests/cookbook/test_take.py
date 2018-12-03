from pygears.cookbook import take
from pygears.cookbook.verif import directed, verif
from pygears.sim import sim
from pygears.sim.modules.drv import drv
from pygears.typing import Queue, Uint, Tuple

t_din = Queue[Tuple[Uint[16], Uint[16]]]
t_din_sep = Queue[Uint[16]]
t_cfg = Uint[16]


def test_directed(tmpdir, sim_cls):
    seq = []
    tmp = []
    for i in range(9):
        tmp.append((i, 2))
    seq.append(tmp)

    tmp = []
    for i in range(5):
        tmp.append((i, 3))
    seq.append(tmp)

    directed(
        drv(t=t_din, seq=seq),
        f=take(sim_cls=sim_cls),
        ref=[[0, 1], [0, 1, 2]])

    sim(outdir=tmpdir)


def test_directed_two_inputs(tmpdir, sim_cls):
    verif(
        drv(t=t_din_sep, seq=[list(range(9)), list(range(5))]),
        drv(t=t_cfg, seq=[2, 3]),
        f=take(sim_cls=sim_cls),
        ref=take(name='ref_model'))

    sim(outdir=tmpdir)
