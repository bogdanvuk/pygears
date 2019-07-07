from pygears.lib import flatten
from pygears.typing import Queue, Uint, Unit
from pygears.lib.verif import drv, verif
from pygears import sim


def test_full_flat_cosim(tmpdir, cosim_cls):
    verif(drv(t=Queue[Uint[4], 3], seq=[[[list(range(4))]]]),
          f=flatten(lvl=3, sim_cls=cosim_cls),
          ref=flatten(lvl=3, name='ref_model'))

    sim(outdir=tmpdir)


def test_dout_queue_lvl_1_cosim(tmpdir, cosim_cls):
    verif(drv(t=Queue[Uint[4], 2], seq=[[list(range(4)) for _ in range(2)]]),
          f=flatten(sim_cls=cosim_cls),
          ref=flatten(name='ref_model'))

    sim(outdir=tmpdir)


def test_dout_queue_lvl_2_cosim(tmpdir, cosim_cls):
    verif(drv(t=Queue[Uint[4], 3],
              seq=[[[list(range(2)) for _ in range(2)] for _ in range(2)]]),
          f=flatten(sim_cls=cosim_cls),
          ref=flatten(name='ref_model'))

    sim(outdir=tmpdir)


def test_dout_queue_lvl_2_no_datacosim(tmpdir, cosim_cls):
    verif(drv(t=Queue[Unit, 3],
              seq=[[[[Unit() for _ in range(2)] for _ in range(2)]
                    for _ in range(2)]]),
          f=flatten(sim_cls=cosim_cls),
          ref=flatten(name='ref_model'))

    sim(outdir=tmpdir)
