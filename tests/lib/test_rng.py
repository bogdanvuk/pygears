import pytest

from pygears import Intf, find, gear
from pygears.lib import decouple
from pygears.lib.delay import delay_rng
from pygears.lib.rng import py_rng, qrange
from pygears.lib.verif import directed, drv, verif
from pygears.sim import sim
from pygears.typing import Int, Queue, Tuple, Uint
from pygears.util.test_utils import formal_check


def test_stop_unsigned(tmpdir, sim_cls):
    directed(drv(t=Uint[4], seq=[4]),
             f=qrange(sim_cls=sim_cls),
             ref=[list(range(4))])
    sim(resdir=tmpdir)

def test_stop_signed(tmpdir, sim_cls):
    directed(drv(t=Int[4], seq=[7]),
             f=qrange(sim_cls=sim_cls),
             ref=[list(range(7))])
    sim(resdir=tmpdir)


def test_stop_inclusive(tmpdir, sim_cls):
    directed(drv(t=Uint[4], seq=[4]),
             f=qrange(inclusive=True, sim_cls=sim_cls),
             ref=[list(range(5))])
    sim(resdir=tmpdir)

def test_start_stop(tmpdir, sim_cls):
    directed(drv(t=Tuple[Uint[2], Uint[4]], seq=[(2, 10)]),
             f=qrange(sim_cls=sim_cls),
             ref=[list(range(2, 10))])
    sim(resdir=tmpdir)

# from pygears.sim.modules import SimVerilated
# test_start_stop('/tools/home/tmp/start_stop', SimVerilated)


def test_start_stop_inclusive(tmpdir, sim_cls):
    directed(drv(t=Tuple[Uint[2], Uint[4]], seq=[(2, 10)]),
             f=qrange(inclusive=True, sim_cls=sim_cls),
             ref=[list(range(2, 11))])
    sim(resdir=tmpdir)


def test_start_stop_signed(tmpdir, sim_cls):
    directed(drv(t=Tuple[Int[2], Int[4]], seq=[(-2, 7)]),
             f=qrange(sim_cls=sim_cls),
             ref=[list(range(-2, 7))])
    sim(resdir=tmpdir)

def test_start_stop_combined(tmpdir, sim_cls):
    directed(drv(t=Tuple[Int[2], Uint[4]], seq=[(-2, 7)]),
             f=qrange(sim_cls=sim_cls),
             ref=[list(range(-2, 7))])
    sim(resdir=tmpdir)

# def test_basic_unsigned():
#     iout = qrange(Intf(Tuple[Uint[4], Uint[4], Uint[2]]))
#     assert iout.dtype == Queue[Uint[4]]


# def test_basic_unsigned_sim(tmpdir):
#     seq = [(2, 8, 2)]
#     ref = [list(range(*seq[0]))]

#     directed(drv(t=Tuple[Uint[4], Uint[4], Uint[2]], seq=seq), f=rng, ref=ref)

#     sim(resdir=tmpdir)


# def get_dut(dout_delay):
#     @gear
#     def decoupled(din, *, cnt_steps=False, incr_steps=False):
#         return din | rng(cnt_steps=cnt_steps, incr_steps=incr_steps) | decouple

#     if dout_delay == 0:
#         return decoupled
#     return rng


# @pytest.mark.parametrize('din_delay', [0, 5])
# @pytest.mark.parametrize('dout_delay', [0, 5])
# @pytest.mark.parametrize('cnt_steps', [True, False])
# @pytest.mark.parametrize('incr_steps', [True, False])
# def test_unsigned_cosim(tmpdir, cosim_cls, din_delay, dout_delay, cnt_steps,
#                         incr_steps):
#     # from pygears.sim.modules import SimVerilated
#     # from functools import partial
#     # from pygears import config

#     # cosim_cls = partial(SimVerilated, language='v')
#     # tmpdir = '/tools/home/tmp'
#     # config['debug/trace'] = ['*']
#     # cnt_steps = False
#     # incr_steps = True
#     # dout_delay = 5

#     seq = [(2, 8, 2)]

#     dut = get_dut(dout_delay)
#     verif(drv(t=Tuple[Uint[4], Uint[4], Uint[2]], seq=seq)
#           | delay_rng(din_delay, din_delay),
#           f=dut(sim_cls=cosim_cls, cnt_steps=cnt_steps, incr_steps=incr_steps),
#           ref=rng(name='ref_model', cnt_steps=cnt_steps,
#                   incr_steps=incr_steps),
#           delays=[delay_rng(dout_delay, dout_delay)])

#     sim(resdir=tmpdir)


# def test_basic_signed():
#     iout = rng(Intf(Tuple[Int[4], Int[6], Uint[2]]))
#     assert iout.dtype == Queue[Int[6]]


# def test_basic_signed_sim(tmpdir):
#     seq = [(-15, -3, 2)]
#     ref = [list(range(*seq[0]))]

#     directed(drv(t=Tuple[Int[5], Int[6], Uint[2]], seq=seq), f=rng, ref=ref)

#     sim(resdir=tmpdir)


# @pytest.mark.parametrize('din_delay', [0, 5])
# @pytest.mark.parametrize('dout_delay', [0, 5])
# def test_signed_cosim(tmpdir, cosim_cls, din_delay, dout_delay):
#     seq = [(-15, -3, 2)]

#     dut = get_dut(dout_delay)
#     verif(drv(t=Tuple[Int[5], Int[6], Uint[2]], seq=seq)
#           | delay_rng(din_delay, din_delay),
#           f=dut(sim_cls=cosim_cls),
#           ref=rng(name='ref_model'),
#           delays=[delay_rng(dout_delay, dout_delay)])

#     sim(resdir=tmpdir)


# def test_supply_constant():
#     iout = rng((Uint[4](0), 8, 1))

#     rng_gear = find('/rng/py_rng')

#     assert iout.dtype == Queue[Uint[4]]
#     assert rng_gear.params['cfg'] == Tuple[{
#         'start': Uint[4],
#         'cnt': Uint[4],
#         'incr': Uint[1]
#     }]


# def test_cnt_only():
#     iout = rng(8)

#     assert iout.dtype == Queue[Uint[4]]

#     rng_gear = find('/rng/rng/py_rng')
#     assert rng_gear.params['cfg'] == Tuple[Uint[1], Uint[4], Uint[1]]


# def test_cnt_only_sim(tmpdir):
#     seq = [8]
#     ref = [list(range(8))]

#     directed(drv(t=Uint[4], seq=seq), f=rng, ref=ref)

#     sim(resdir=tmpdir)


# @pytest.mark.parametrize('din_delay', [0, 5])
# @pytest.mark.parametrize('dout_delay', [0, 5])
# def test_cnt_only_cosim(tmpdir, cosim_cls, din_delay, dout_delay):
#     seq = [8]

#     verif(drv(t=Uint[4], seq=seq)
#           | delay_rng(din_delay, din_delay),
#           f=rng(sim_cls=cosim_cls),
#           ref=rng(name='ref_model'),
#           delays=[delay_rng(dout_delay, dout_delay)])

#     sim(resdir=tmpdir)


# def test_cnt_down():
#     iout = rng((7, 0, -1))

#     rng_gear = find('/rng/py_rng')

#     assert rng_gear.params['cfg'] == Tuple[Int[4], Int[2], Int[1]]
#     assert iout.dtype == Queue[Int[4]]


# # @pytest.mark.xfail(raises=MultiAlternativeError)
# # def test_multi_lvl():
# #     iout = rng((1, 2, 3), lvl=2)
# #     print(iout.dtype)

# # @hdl_check(['rng_hier.sv'])
# # def test_basic_unsigned_svgen():
# #     rng(Intf(Tuple[Uint[4], Uint[2], Uint[2]]))

# # @hdl_check(['rng_rng.sv', 'rng_ccat.sv', 'rng_hier.sv'])
# # def test_cnt_svgen():
# #     rng(8)

# # TODO : hierarchy must be avoided for verilog (so py_rng, not rng)


# @formal_check()
# def test_basic_formal():
#     py_rng(Intf(Tuple[Uint[4], Uint[4], Uint[2]]))


# @formal_check()
# def test_cnt_steps_formal():
#     py_rng(Intf(Tuple[Uint[4], Uint[4], Uint[2]]), cnt_steps=True)


# @formal_check()
# def test_incr_cnt_steps_formal():
#     py_rng(Intf(Tuple[Uint[4], Uint[4], Uint[2]]),
#            cnt_steps=True,
#            incr_steps=True)
