import random
from functools import partial

import pytest

from pygears import Intf, gear
from pygears.lib import decouple
from pygears.lib.delay import delay_rng
from pygears.lib.trr import trr
from pygears.lib.verif import directed, drv, verif
from pygears.sim import sim
from pygears.sim.extens.randomization import create_constraint, rand_seq
from pygears.sim.extens.svrand import SVRandSocket
from pygears.sim.modules.sim_socket import SimSocket
from pygears.typing import Queue, Uint
from pygears.util.test_utils import formal_check, skip_ifndef, synth_check

T_DIN = Queue[Uint[16]]


def get_dut(dout_delay):
    @gear
    def decoupled(*din):
        return din | trr | decouple

    if dout_delay == 0:
        return decoupled
    return trr


@pytest.mark.parametrize('din_delay', [0, 1])
@pytest.mark.parametrize('dout_delay', [0, 1])
def test_directed(tmpdir, sim_cls, din_delay, dout_delay):
    dut = get_dut(dout_delay)
    directed(
        drv(t=T_DIN, seq=[list(range(9)), list(range(3))])
        | delay_rng(din_delay, din_delay),
        drv(t=T_DIN, seq=[list(range(9)), list(range(3))])
        | delay_rng(din_delay, din_delay),
        drv(t=T_DIN, seq=[list(range(9)), list(range(3))])
        | delay_rng(din_delay, din_delay),
        f=dut(sim_cls=sim_cls),
        ref=[[[0, 1, 2, 3, 4, 5, 6, 7, 8], [0, 1, 2, 3, 4, 5, 6, 7, 8],
              [0, 1, 2, 3, 4, 5, 6, 7, 8]], [[0, 1, 2], [0, 1, 2], [0, 1, 2]]],
        delays=[delay_rng(dout_delay, dout_delay)])

    sim(outdir=tmpdir)


def test_random(tmpdir, sim_cls):
    skip_ifndef('RANDOM_TEST')

    din_num = 3

    stim = []
    for _ in range(din_num):
        stim.append(
            drv(t=T_DIN,
                seq=[
                    list(range(random.randint(1, 10))),
                    list(range(random.randint(1, 10)))
                ]))

    verif(*stim, f=trr(sim_cls=sim_cls), ref=trr(name='ref_model'))

    sim(outdir=tmpdir)


def test_socket_cosim_rand(tmpdir):
    skip_ifndef('SIM_SOCKET_TEST', 'RANDOM_TEST')

    din_num = 3

    cons = []
    for i in range(din_num):
        cons.append(
            create_constraint(T_DIN, f'din{i}', eot_cons=['data_size == 10']))

    stim = []
    for i in range(din_num):
        stim.append(drv(t=T_DIN, seq=rand_seq(f'din{i}', 30)))

    verif(
        *stim,
        f=trr(sim_cls=partial(SimSocket, run=True)),
        ref=trr(name='ref_model'))

    sim(outdir=tmpdir, extens=[partial(SVRandSocket, cons=cons)])


@formal_check()
def test_formal():
    trr(Intf(T_DIN), Intf(T_DIN), Intf(T_DIN))


@synth_check({'logic luts': 24, 'ffs': 2}, tool='vivado')
def test_trr_vivado():
    trr(Intf(T_DIN), Intf(T_DIN), Intf(T_DIN))


@synth_check({'logic luts': 25, 'ffs': 2}, tool='yosys')
def test_trr_yosys():
    trr(Intf(T_DIN), Intf(T_DIN), Intf(T_DIN))
