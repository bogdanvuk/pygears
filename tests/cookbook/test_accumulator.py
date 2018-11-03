
from pygears.cookbook import accumulator
from pygears.cookbook.delay import delay_rng
from pygears.cookbook.verif import directed, verif
from pygears.sim import sim
from pygears.sim.modules.drv import drv
from pygears.sim.modules.verilator import SimVerilated
from pygears.typing import Int, Queue, Tuple, Uint
from pygears.util.test_utils import skip_ifndef

seq_uint = [[(1, 2), (5, 2), (8, 2)], [(3, 8), (1, 8)], [(0, 12), (4, 12),
                                                         (2, 12), (99, 12)]]
ref_uint = [16, 12, 117]
t_din_uint = Queue[Tuple[Uint[16], Uint[16]]]

seq_int = [[(1, 2), (5, 2), (-8, 2)], [(-30, 8), (1, 8)]]
ref_int = [0, -21]
t_din_int = Queue[Tuple[Int[8], Int[8]]]


def test_pysim_uint():
    directed(drv(t=t_din_uint, seq=seq_uint), f=accumulator, ref=ref_uint)
    sim()


def test_pysim_int():
    directed(drv(t=t_din_int, seq=seq_int), f=accumulator, ref=ref_int)
    sim()


def test_verilator_uint(tmpdir):
    skip_ifndef('VERILATOR_ROOT')
    verif(
        drv(t=t_din_uint, seq=seq_uint),
        f=accumulator(sim_cls=SimVerilated),
        ref=accumulator(name='ref_model'))
    sim(outdir=tmpdir)


def test_verilator_int(tmpdir):
    skip_ifndef('VERILATOR_ROOT')
    verif(
        drv(t=t_din_int, seq=seq_int),
        f=accumulator(sim_cls=SimVerilated),
        ref=accumulator(name='ref_model'))
    sim(outdir=tmpdir)


def test_verilator_delay(tmpdir):
    skip_ifndef('VERILATOR_ROOT')
    verif(
        drv(t=t_din_uint, seq=seq_uint) | delay_rng(2, 2),
        f=accumulator(sim_cls=SimVerilated),
        ref=accumulator(name='ref_model'),
        delays=[delay_rng(5, 5)])
    sim(outdir=tmpdir)
