import pytest

from pygears import Intf
from pygears.lib import add, directed, drv, verif
from pygears.sim import sim
from pygears.typing import Int, Tuple, Uint, Ufixp, Fixp
from pygears.util.test_utils import synth_check
from pygears.sim.extens.randomization import randomize, rand_seq

# def test_unsigned_overflow_cosim(cosim_cls=None):
#     seq = [(0x1, 0xf), (0x2, 0xe), (0x3, 0xd)]

#     operands_t = Tuple[{'a': Uint[2], 'b': Uint[4]}]

#     # verif(drv(t=Tuple[Uint[2], Uint[4]], seq=seq),

#     verif(
#         drv(t=operands_t,
#             seq=randomize(operands_t, 'din', cnt=4,
#                           cons=['din.a + din.b > 8'])),
#         f=add,
#         ref=add(name='ref_model'))

#     from pygears.sim import cosim
#     cosim('/add', 'xsim', run=True)
#     sim()

# test_unsigned_overflow_cosim('/tools/home/tmp/simsock')


def test_signed_unsigned_cosim(cosim_cls):
    seq = [(0x1, 0xf), (-0x2, 0xf), (0x1, 0x0), (-0x2, 0x0)]

    verif(drv(t=Tuple[Int[2], Uint[4]], seq=seq),
          f=add(sim_cls=cosim_cls),
          ref=add(name='ref_model'))

    sim()


def test_unsigned_signed_cosim(cosim_cls):
    seq = [(0x1, 0x7), (0x1, -0x8), (0x2, 0x7), (0x2, -0x8)]

    verif(drv(t=Tuple[Uint[2], Int[4]], seq=seq),
          f=add(sim_cls=cosim_cls),
          ref=add(name='ref_model'))

    sim()


def test_signed_cosim(cosim_cls):
    seq = [(0x1, 0x7), (-0x2, 0x7), (0x1, -0x8), (-0x2, -0x8)]

    verif(drv(t=Tuple[Int[2], Int[4]], seq=seq),
          f=add(sim_cls=cosim_cls),
          ref=add(name='ref_model'))

    sim()


@synth_check({'logic luts': 33}, top='/add', tool='vivado')
def test_unsigned_synth_vivado():
    add(Intf(Uint[32]), Intf(Uint[32]))


# @synth_check({'logic luts': 67}, tool='yosys')
# def test_unsigned_synth_yosys():
#     add(Intf(Uint[32]), Intf(Uint[32]))


@synth_check({'logic luts': 6}, top='/add', tool='vivado')
def test_signed_unsigned_synth_vivado():
    add(Intf(Int[2]), Intf(Uint[4]))


# @synth_check({'logic luts': 11}, tool='yosys')
# def test_signed_unsigned_synth_yosys():
#     add(Intf(Int[2]), Intf(Uint[4]))


def test_ufixp(sim_cls):
    directed(drv(t=Ufixp[2, 3], seq=[2.5, 0]),
             drv(t=Ufixp[3, 4], seq=[3.5, 0]),
             f=add(sim_cls=sim_cls),
             ref=[6.0, 0.0])
    sim()


def test_fixp(sim_cls):
    directed(drv(t=Fixp[2, 4], seq=[1.75, 1.75, 0, -2.0, -2.0]),
             drv(t=Fixp[3, 6], seq=[3.875, -4.0, 0, 3.875, -4.0]),
             f=add(sim_cls=sim_cls),
             ref=[5.625, -2.25, 0, 1.875, -6.0])
    sim()


@pytest.mark.parametrize('count', list(range(2, 7)))
def test_adder_tree(sim_cls, count):
    elems = 4

    vals = [[Fixp[c, 2 * c + elems].decode(i) for i in range(elems)] for c in range(count)]

    refs = [0] * elems
    for v in vals:
        for i, e in enumerate(v):
            refs[i] += float(e)

    drvs = [
        drv(t=Fixp[c, 2 * c + elems], seq=vals[c])
        for c in range(count)
    ]

    directed(*drvs, f=add(sim_cls=sim_cls), ref=refs)
    sim()
