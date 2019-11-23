import random
from functools import partial

import pytest

from pygears import Intf, gear
from pygears.lib import decouple
from pygears.lib.delay import delay_rng
from pygears.lib.deal import qdeal
from pygears.lib.verif import directed, drv, verif
from pygears.sim import sim
from pygears.sim.extens.randomization import randomize, rand_seq
from pygears.sim.extens.svrand import SVRandSocket
from pygears.sim.modules.sim_socket import SimSocket
from pygears.typing import Queue, Uint
from pygears.util.test_utils import formal_check, skip_ifndef, synth_check

T_TRR_DIST = Queue[Uint[16], 2]


def get_dut(dout_delay):
    @gear
    def decoupled(din, *, lvl=1, num):
        res = din | qdeal(num=num, lvl=lvl)
        dout = []
        for r in res:
            dout.append(r | decouple)
        return tuple(dout)

    if dout_delay == 0:
        return decoupled
    return qdeal


def get_refs(seq):
    ref0 = [seq[0][0], seq[1][0]]
    ref1 = [seq[0][1], seq[1][1]]
    return [ref0, ref1]


@pytest.mark.parametrize('din_delay', [0, 5])
@pytest.mark.parametrize('dout_delay', [0, 5])
def test_directed(tmpdir, sim_cls, din_delay, dout_delay):
    seq = [[list(range(8)), list(range(2)),
            list(range(3))], [list(range(1)), list(range(2))]]

    ref0 = [seq[0][0], seq[0][2], seq[1][0]]
    ref1 = [seq[0][1], seq[1][1]]
    ref = [ref0, ref1]
    dut = get_dut(dout_delay)
    directed(
        drv(t=T_TRR_DIST, seq=seq) | delay_rng(din_delay, din_delay),
        f=dut(sim_cls=sim_cls, num=2),
        ref=ref,
        delays=[
            delay_rng(dout_delay, dout_delay),
            delay_rng(dout_delay, dout_delay)
        ])

    sim(tmpdir)


@pytest.mark.parametrize('din_delay', [0, 5])
@pytest.mark.parametrize('dout_delay', [0, 5])
def test_directed_3in(tmpdir, sim_cls, din_delay, dout_delay):
    t_deal = Queue[Uint[16], 3]
    num = 3
    lvl = 2

    seq = [
        [[list(range(3)), list(range(5))],
         [list(range(1)), list(range(4)), list(range(4)), list(range(8))]],

        [[list(range(3)), list(range(5)), list(range(1))],
         [list(range(1)), list(range(8))],
         [list(range(4))]],

        [[list(range(3)), list(range(1))], [list(range(1))]]
        ]

    ref0 = [seq[0][0], seq[1][0], seq[2][0]]
    ref1 = [seq[0][1], seq[1][1], seq[2][1]]
    ref2 = [seq[1][2]]
    ref = [ref0, ref1, ref2]
    dout_dly = [delay_rng(dout_delay, dout_delay)] * num

    dut = get_dut(dout_delay)
    directed(
        drv(t=t_deal, seq=seq) | delay_rng(din_delay, din_delay),
        f=dut(sim_cls=sim_cls, lvl=lvl, num=num),
        ref=ref,
        delays=dout_dly)

    sim(tmpdir)


def test_random(tmpdir, sim_cls):
    skip_ifndef('RANDOM_TEST')

    seq = [[
        list(range(random.randint(1, 10))),
        list(range(random.randint(1, 5)))
    ], [list(range(random.randint(1, 20))),
        list(range(random.randint(1, 7)))]]

    directed(drv(t=T_TRR_DIST, seq=seq),
             f=qdeal(sim_cls=sim_cls, num=2),
             ref=get_refs(seq))

    sim(tmpdir)


def test_socket_rand_cons(tmpdir):
    skip_ifndef('SIM_SOCKET_TEST', 'RANDOM_TEST')

    cons = []
    cons.append(
        randomize(T_TRR_DIST,
                          'din',
                          eot_cons=['data_size == 50', 'trans_lvl1[0] == 4']))

    verif(drv(t=Queue[Uint[16], 2], seq=rand_seq('din', 30)),
          f=qdeal(sim_cls=partial(SimSocket, run=True), num=2),
          ref=qdeal(name='ref_model', num=2))

    sim(tmpdir, extens=[partial(SVRandSocket, cons=cons)])


@formal_check()
def test_formal():
    qdeal(Intf(T_TRR_DIST), num=2)


@formal_check()
def test_lvl_2_formal():
    qdeal(Intf(Queue[Uint[16], 3]), num=3, lvl=2)


@synth_check({'logic luts': 4, 'ffs': 1}, tool='vivado')
def test_synth_vivado():
    qdeal(Intf(T_TRR_DIST), num=2)


@synth_check({'logic luts': 5, 'ffs': 1}, tool='yosys')
def test_synth_yosys():
    qdeal(Intf(T_TRR_DIST), num=2)
