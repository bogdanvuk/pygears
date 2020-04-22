
from pygears.lib.rng import qrange
from pygears.lib.verif import directed, drv
from pygears.sim import sim
from pygears.typing import Int, Tuple, Uint


def test_stop_unsigned(sim_cls):
    directed(drv(t=Uint[4], seq=[4]),
             f=qrange(sim_cls=sim_cls),
             ref=[list(range(4))])
    sim()


def test_stop_signed(sim_cls):
    directed(drv(t=Int[4], seq=[7]),
             f=qrange(sim_cls=sim_cls),
             ref=[list(range(7))])
    sim()


def test_stop_inclusive(sim_cls):
    directed(drv(t=Uint[4], seq=[4]),
             f=qrange(inclusive=True, sim_cls=sim_cls),
             ref=[list(range(5))])
    sim()


def test_start_stop(sim_cls):
    directed(drv(t=Tuple[Uint[2], Uint[4]], seq=[(2, 10)]),
             f=qrange(sim_cls=sim_cls),
             ref=[list(range(2, 10))])
    sim()


def test_start_stop_inclusive(sim_cls):
    directed(drv(t=Tuple[Uint[2], Uint[4]], seq=[(2, 10)]),
             f=qrange(inclusive=True, sim_cls=sim_cls),
             ref=[list(range(2, 11))])
    sim()


def test_start_stop_signed(sim_cls):
    directed(drv(t=Tuple[Int[2], Int[4]], seq=[(-2, 7)]),
             f=qrange(sim_cls=sim_cls),
             ref=[list(range(-2, 7))])
    sim()


def test_start_stop_combined(sim_cls):
    directed(drv(t=Tuple[Int[2], Uint[4]], seq=[(-2, 7)]),
             f=qrange(sim_cls=sim_cls),
             ref=[list(range(-2, 7))])
    sim()

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
