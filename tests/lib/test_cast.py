from pygears.lib import cast as cast_gear, code as code_gear
from pygears.typing import Tuple, Uint, Queue, Int, Ufixp, cast
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


def cast_cosim_test(src_type,
                    cast_type,
                    seq,
                    expected,
                    module=cast_gear):
    skip_ifndef('VERILATOR_ROOT')

    report = verif(drv(t=src_type, seq=seq),
                   f=module(sim_cls=SimVerilated, t=cast_type),
                   ref=module(name='ref_model', t=cast_type), make_report=True)

    sim()

    for e, rep in zip(expected, report[0]):
        assert e == rep['items'][0]


def test_signed_signed_more_cosim():
    cast_cosim_test(Int[4],
                    Int[6],
                    seq=[-0x8, 0x7],
                    expected=[Int[6](-0x8), Int[6](7)])


def test_signed_signed_less_cosim():
    cast_cosim_test(Int[4],
                    Int[2],
                    seq=[-0x8, 0x7],
                    expected=[Int[2](0), Int[2](-1)],
                    module=code_gear)


def test_signed_unsigned_more_cosim():
    cast_cosim_test(Int[4],
                    Uint[6],
                    seq=[-0x8, 0x7],
                    expected=[Uint[6](-0x8 & 0xf), Uint[6](7)],
                    module=code_gear)


def test_signed_unsigned_less_cosim():
    cast_cosim_test(Int[4],
                    Uint[3],
                    seq=[-0x8, 0x7],
                    expected=[Uint[3](0), Uint[3](7)],
                    module=code_gear)


def test_unsigned_signed_same_cosim():
    cast_cosim_test(Uint[4],
                    Int[4],
                    seq=[0xf, 0x7],
                    expected=[Int[4](-1), Int[4](7)],
                    module=code_gear)


def test_unsigned_signed_more_cosim():
    cast_cosim_test(Uint[4],
                    Int[5],
                    seq=[0xf, 0x7],
                    expected=[Int[5](0xf), Int[5](0x7)])


def test_unsigned_signed_less_cosim():
    cast_cosim_test(Uint[4],
                    Int[2],
                    seq=[0xf, 0x7],
                    expected=[Int[2](-1), Int[2](-1)],
                    module=code_gear)


def test_tuple_cosim():
    cast_cosim_test(Tuple[Uint[4], Int[2]],
                    Tuple[Int[5], Int[4]],
                    seq=[(3, -2), (1, 1)],
                    expected=[(3, -2), (1, 1)])


def test_ufixp_cosim():
    cast_cosim_test(Ufixp[4, 6],
                    Ufixp[2, 3],
                    seq=[2.75, 4.0],
                    expected=[Ufixp[2, 3](1.5), Ufixp[2, 3](0.0)],
                    module=code_gear)
