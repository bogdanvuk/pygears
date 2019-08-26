from pygears import cast
from pygears.lib import cast as cast_gear
from pygears.typing import Tuple, Uint, Queue, Int, Ufixp
from pygears import Intf
from pygears.util.test_utils import skip_ifndef
from pygears.lib.verif import verif
from pygears.sim import sim
from pygears.lib.verif import drv
from pygears.sim.modules.verilator import SimVerilated


def test_type_queue_to_tuple():
    a = Queue[Tuple[Uint[1], Uint[2]], 3]
    assert cast(a, Tuple) == Tuple[Tuple[Uint[1], Uint[2]], Uint[3]]


def test_queue_to_tuple():
    iout = Intf(Queue[Tuple[Uint[1], Uint[2]], 3]) | Tuple
    assert iout.dtype == Tuple[Tuple[Uint[1], Uint[2]], Uint[3]]


def cast_cosim_test(tmpdir, src_type, cast_type, seq, expected):
    skip_ifndef('VERILATOR_ROOT')

    report = verif(drv(t=src_type, seq=seq),
                   f=cast_gear(sim_cls=SimVerilated, cast_type=cast_type),
                   ref=cast_gear(name='ref_model', cast_type=cast_type))

    sim(outdir=tmpdir)

    for e, rep in zip(expected, report[0]):
        assert e == rep['items'][0]


def test_signed_signed_more_cosim(tmpdir):
    cast_cosim_test(tmpdir,
                    Int[4],
                    Int[6],
                    seq=[-0x8, 0x7],
                    expected=[Int[6](-0x8), Int[6](7)])


def test_signed_signed_less_cosim(tmpdir):
    cast_cosim_test(tmpdir,
                    Int[4],
                    Int[2],
                    seq=[-0x8, 0x7],
                    expected=[Int[2](0), Int[2](-1)])


def test_signed_unsigned_more_cosim(tmpdir):
    cast_cosim_test(tmpdir,
                    Int[4],
                    Uint[6],
                    seq=[-0x8, 0x7],
                    expected=[Uint[6](-0x8 & 0x3f), Uint[6](7)])


def test_signed_unsigned_less_cosim(tmpdir):
    cast_cosim_test(tmpdir,
                    Int[4],
                    Uint[3],
                    seq=[-0x8, 0x7],
                    expected=[Uint[3](0), Uint[3](7)])


def test_unsigned_signed_same_cosim(tmpdir):
    cast_cosim_test(tmpdir,
                    Uint[4],
                    Int[4],
                    seq=[0xf, 0x7],
                    expected=[Int[4](-1), Int[4](7)])


def test_unsigned_signed_less_cosim(tmpdir):
    cast_cosim_test(tmpdir,
                    Uint[4],
                    Int[2],
                    seq=[0xf, 0x7],
                    expected=[Int[2](-1), Int[2](-1)])


def test_ufixp_cosim(tmpdir):
    cast_cosim_test(tmpdir,
                    Ufixp[4, 6],
                    Ufixp[2, 3],
                    seq=[2.75, 4.0],
                    expected=[Ufixp[2, 3](2.5), Ufixp[3, 4](0.0)])
