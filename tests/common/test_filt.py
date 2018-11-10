import pytest
import random
from functools import partial

from pygears.common import filt, filt_by
from pygears.cookbook.verif import directed
from pygears.sim import sim
from pygears.sim.modules.drv import drv
from pygears.sim.modules.sim_socket import SimSocket
from pygears.sim.modules.verilator import SimVerilated
from pygears.typing import Uint, Union, Queue, typeof
from pygears.util.test_utils import skip_ifndef

plain_din = Uint[8]
union_din = Union[Uint[8], Uint[8], Uint[8]]
queue_din = Queue[Union[Uint[8], Uint[8], Uint[8]]]

directed_seq = [(v, v % 2) for v in range(50)]


def pysim_env(din_t, seq, sel, ref, sim_cls):
    directed(drv(t=din_t, seq=seq), f=filt(sim_cls=sim_cls, sel=sel), ref=ref)
    sim()


def filt_test(din_t, seq, sel, sim_cls):
    pysim_env(din_t, seq, sel, [val for (val, ctrl) in seq if (ctrl == sel)],
              sim_cls)


def filt_by_test(din_t, seq, sel, sim_cls):
    din_seq, ctrl_seq = zip(*seq)

    din_drv = drv(t=din_t, seq=din_seq)
    ctrl_drv = drv(t=Uint[2], seq=ctrl_seq)

    directed(
        din_drv,
        f=filt_by(ctrl_drv, sim_cls=sim_cls, sel=sel),
        ref=[val for (val, ctrl) in zip(din_seq, ctrl_seq) if (ctrl == sel)])
    sim()


def queue_filt_test(din_t, seq, sel, sim_cls):
    pysim_env(din_t, [seq], sel,
              [[val for (val, ctrl) in seq if (ctrl == sel)]], sim_cls)


@pytest.mark.parametrize('sel', [0, 1])
@pytest.mark.parametrize('din_t', [union_din, queue_din, plain_din])
@pytest.mark.parametrize('seq', [directed_seq, 'rand'])
@pytest.mark.parametrize('sim_cls', [None, SimVerilated, SimSocket])
def test_pysim_dir(sel, din_t, seq, sim_cls):
    if seq == 'rand':
        skip_ifndef('RANDOM_TEST')
        seq = [(random.randint(1, 100), random.randint(0, 2))
               for _ in range(random.randint(10, 50))]

    if sim_cls is SimVerilated:
        skip_ifndef('VERILATOR_ROOT')
    elif sim_cls is SimSocket:
        skip_ifndef('SIM_SOCKET_TEST')
        sim_cls = partial(SimSocket, run=True)

    if typeof(din_t, Queue):
        queue_filt_test(din_t, seq, sel, sim_cls)
    elif typeof(din_t, Union):
        filt_test(din_t, seq, sel, sim_cls)
    else:
        filt_by_test(din_t, seq, sel, sim_cls)
