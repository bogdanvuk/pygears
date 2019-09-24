import random
from functools import partial

import pytest

from pygears import Intf, gear
from pygears.lib import decouple
from pygears.lib import chop, delay_rng, directed, verif
from pygears.sim import sim
from pygears.sim.extens.randomization import create_constraint, rand_seq
from pygears.sim.extens.scvrand import SCVRand
from pygears.sim.extens.svrand import SVRandSocket
from pygears.lib.verif import drv
from pygears.sim.modules.sim_socket import SimSocket
from pygears.sim.modules.verilator import SimVerilated
from pygears.typing import Queue, Tuple, Uint
from pygears.util.test_utils import formal_check, skip_ifndef

t_din = Queue[Uint[16]]
t_cfg = Uint[16]


def get_dut(dout_delay):
    @gear
    def decoupled(*din):
        return din | chop | decouple

    if dout_delay == 0:
        return decoupled
    return chop


def get_stim():
    cfg_seq = []
    din_seq = []
    cfg_num = random.randint(2, 10)
    for _ in range(cfg_num):
        cfg_seq.append(random.randint(1, 10))
        din_seq.append(list(range(random.randint(1, 10))))

    return [drv(t=t_din, seq=din_seq), drv(t=t_cfg, seq=cfg_seq)]


@pytest.mark.parametrize('din_delay', [0, 1])
@pytest.mark.parametrize('dout_delay', [0, 1])
def test_directed(tmpdir, sim_cls, din_delay, dout_delay):
    dut = get_dut(dout_delay)
    directed(
        drv(t=t_din, seq=[list(range(9)), list(range(3))])
        | delay_rng(din_delay, din_delay),
        drv(t=t_cfg, seq=[2, 3]) | delay_rng(din_delay, din_delay),
        f=dut(sim_cls=sim_cls),
        ref=[[0, 1], [2, 3], [4, 5], [6, 7], [8], [0, 1, 2]],
        delays=[delay_rng(dout_delay, dout_delay)])
    sim(resdir=tmpdir)


def test_random(tmpdir, sim_cls):
    skip_ifndef('RANDOM_TEST')
    stim = get_stim()
    verif(*stim, f=chop(sim_cls=sim_cls), ref=chop(name='ref_model'))
    sim(resdir=tmpdir)


def test_socket_rand_cons(tmpdir):
    skip_ifndef('SIM_SOCKET_TEST', 'RANDOM_TEST')

    cnt = 5

    cons = []
    cons.append(create_constraint(t_din, 'din', eot_cons=['data_size == 20']))
    cons.append(create_constraint(t_cfg, 'cfg', cons=['cfg < 20', 'cfg > 0']))

    stim = []

    stim.append(drv(t=t_din, seq=rand_seq('din', cnt)))
    stim.append(drv(t=t_cfg, seq=rand_seq('cfg', cnt)))

    verif(
        *stim,
        f=chop(sim_cls=partial(SimSocket, run=True)),
        ref=chop(name='ref_model'))

    sim(resdir=tmpdir, extens=[partial(SVRandSocket, cons=cons)])


def test_open_rand_cons(tmpdir):
    skip_ifndef('VERILATOR_ROOT', 'SCV_HOME', 'RANDOM_TEST')

    cnt = 5

    cons = []
    # TODO : queue constraints not yet supported in SCVRand
    # cons.append(create_constraint(t_din, 'din', eot_cons=['data_size == 20']))
    cons.append(create_constraint(t_cfg, 'cfg', cons=['cfg < 20', 'cfg > 0']))

    stim = []

    din_seq = []
    for i in range(cnt):
        din_seq.append(list(range(random.randint(1, 10))))
    stim.append(drv(t=t_din, seq=din_seq))
    # stim.append(drv(t=t_din, seq=rand_seq('din', cnt)))
    stim.append(drv(t=t_cfg, seq=rand_seq('cfg', cnt)))

    verif(*stim, f=chop(sim_cls=SimVerilated), ref=chop(name='ref_model'))

    sim(resdir=tmpdir, extens=[partial(SCVRand, cons=cons)])


@formal_check()
def test_formal():
    chop(Intf(Queue[Tuple[Uint[16], Uint[16]]]))
