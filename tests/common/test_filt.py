import random
from functools import partial

from nose import with_setup

from pygears import clear
from pygears.common import filt
from pygears.cookbook.verif import directed, verif
from pygears.sim import sim
from pygears.sim.modules.drv import drv
from pygears.sim.modules.sim_socket import SimSocket
from pygears.sim.modules.verilator import SimVerilated
from pygears.typing import Uint, Union, Queue
from utils import prepare_result_dir, skip_ifndef

din_t = Union[Uint[8], Uint[8], Uint[8]]
qdin_t = Queue[Union[Uint[8], Uint[8], Uint[8]]]
dir_seq = [(random.randint(1, 100), random.randint(0, 2))
           for _ in range(random.randint(10, 50))]
rand_seq = [(random.randint(1, 100), random.randint(0, 2))
            for _ in range(random.randint(10, 50))]


@with_setup(clear)
def test_pysim_dir(seq=dir_seq, sel=1):
    directed(
        drv(t=din_t, seq=seq),
        f=filt(sel=sel),
        ref=[x for (x, y) in seq if (y == sel)])
    sim()


@with_setup(clear)
def test_pysim_dir_q(seq=dir_seq, sel=1):
    directed(
        drv(t=qdin_t, seq=[seq]),
        f=filt(sel=sel),
        ref=[[x for (x, y) in seq if (y == sel)]])
    sim()


@with_setup(clear)
def test_pysim_rand(seq=rand_seq, sel=1):
    skip_ifndef('RANDOM_TEST')
    directed(
        drv(t=din_t, seq=seq),
        f=filt(sel=sel),
        ref=[x for (x, y) in seq if (y == sel)])
    sim()


@with_setup(clear)
def test_pysim_rand_q(seq=rand_seq, sel=1):
    skip_ifndef('RANDOM_TEST')
    directed(
        drv(t=qdin_t, seq=[seq]),
        f=filt(sel=sel),
        ref=[[x for (x, y) in seq if (y == sel)]])
    sim()


@with_setup(clear)
def test_socket_dir(seq=dir_seq, sel=0):
    skip_ifndef('SIM_SOCKET_TEST')
    verif(
        drv(t=din_t, seq=seq),
        f=filt(sim_cls=partial(SimSocket, run=True), sel=sel),
        ref=filt(name='ref_model', sel=sel))
    sim(outdir=prepare_result_dir())


@with_setup(clear)
def test_socket_rand(seq=rand_seq, sel=0):
    skip_ifndef('SIM_SOCKET_TEST', 'RANDOM_TEST')
    verif(
        drv(t=din_t, seq=seq),
        f=filt(sim_cls=partial(SimSocket, run=True), sel=sel),
        ref=filt(name='ref_model', sel=sel))
    sim(outdir=prepare_result_dir())


@with_setup(clear)
def test_socket_dir_q(seq=dir_seq, sel=0):
    skip_ifndef('SIM_SOCKET_TEST')
    verif(
        drv(t=qdin_t, seq=[seq]),
        f=filt(
            sim_cls=partial(SimSocket, run=True),
            sel=sel,
        ),
        ref=filt(name='ref_model', sel=sel))
    sim(outdir=prepare_result_dir())


@with_setup(clear)
def test_socket_rand_q(seq=rand_seq, sel=0):
    skip_ifndef('SIM_SOCKET_TEST', 'RANDOM_TEST')
    verif(
        drv(t=qdin_t, seq=[seq]),
        f=filt(
            sim_cls=partial(SimSocket, run=True),
            sel=sel,
        ),
        ref=filt(name='ref_model', sel=sel))
    sim(outdir=prepare_result_dir())


@with_setup(clear)
def test_verilator_dir(seq=dir_seq, sel=0):
    skip_ifndef('VERILATOR_ROOT')
    verif(
        drv(t=din_t, seq=seq),
        f=filt(sim_cls=SimVerilated, sel=sel),
        ref=filt(name='ref_model', sel=sel))
    sim(outdir=prepare_result_dir())


@with_setup(clear)
def test_verilator_rand(seq=rand_seq, sel=0):
    skip_ifndef('VERILATOR_ROOT', 'RANDOM_TEST')
    verif(
        drv(t=din_t, seq=seq),
        f=filt(sim_cls=SimVerilated, sel=sel),
        ref=filt(name='ref_model', sel=sel))
    sim(outdir=prepare_result_dir())
