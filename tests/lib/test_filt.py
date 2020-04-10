import random

import pytest

from pygears import Intf, gear
from pygears.lib import decouple, filt
from pygears.lib.delay import delay_rng
from pygears.lib.verif import directed, drv, verif
from pygears.sim import sim
from pygears.typing import Queue, Tuple, Uint, Union, typeof
from pygears.util.test_utils import skip_ifndef, synth_check
from pygears import datagear
from pygears.typing import Integer, Bool

plain_din = Uint[8]
union_din = Union[Uint[8], Uint[8], Uint[8]]
queue_din = Queue[Union[Uint[8], Uint[8], Uint[8]]]

directed_seq = [union_din(v, v % 2) for v in range(50)]


def pysim_env(din_t, seq, sel, ref, sim_cls):
    directed(drv(t=din_t, seq=seq), f=filt(sim_cls=sim_cls, fixsel=sel), ref=ref)
    sim()


def filt_test(din_t, seq, sel, sim_cls):
    pysim_env(din_t, seq, sel, [val for (val, ctrl) in seq if (ctrl == sel)], sim_cls)


def filt_by_test(tmpdir, din_t, seq, sel, sim_cls):
    din_seq, ctrl_seq = zip(*seq)

    din_drv = drv(t=din_t, seq=din_seq)
    ctrl_drv = drv(t=Uint[2], seq=ctrl_seq)

    @datagear
    def cond(ctrl: Uint, din) -> Bool:
        return ctrl == sel

    directed(
        din_drv,
        f=filt(f=cond(ctrl_drv), sim_cls=sim_cls),
        ref=[val for (val, ctrl) in zip(din_seq, ctrl_seq) if (ctrl == sel)])
    sim(tmpdir)


def queue_filt_test(din_t, seq, sel, sim_cls):
    pysim_env(din_t, [seq], sel, [[val for (val, ctrl) in seq if (ctrl == sel)]], sim_cls)


@pytest.mark.parametrize('sel', [0, 1])
@pytest.mark.parametrize('din_t', [union_din, queue_din, plain_din])
@pytest.mark.parametrize('seq', [directed_seq, 'rand'])
def test_pysim_dir(tmpdir, sel, din_t, seq, sim_cls):
    if seq == 'rand':
        skip_ifndef('RANDOM_TEST')
        seq = [
            (random.randint(1, 100), random.randint(0, 2))
            for _ in range(random.randint(10, 50))
        ]

    if typeof(din_t, Queue):
        queue_filt_test(din_t, seq, sel, sim_cls)
    elif typeof(din_t, Union):
        filt_test(din_t, seq, sel, sim_cls)
    else:
        filt_by_test(tmpdir, din_t, seq, sel, sim_cls)


def get_dut(dout_delay):
    @gear
    def decoupled(din, *, fixsel=0):
        return din | filt(fixsel=fixsel) | decouple

    if dout_delay == 0:
        return decoupled
    return filt


@pytest.mark.parametrize('sel', [0, 1])
@pytest.mark.parametrize('din_delay', [0, 10])
@pytest.mark.parametrize('dout_delay', [0, 10])
def test_qfilt_union_delay(tmpdir, cosim_cls, din_delay, dout_delay, sel):
    dut = get_dut(dout_delay)
    verif(
        drv(t=queue_din, seq=[directed_seq, directed_seq])
        | delay_rng(din_delay, din_delay),
        f=dut(sim_cls=cosim_cls, fixsel=sel),
        ref=filt(name='ref_model', fixsel=sel),
        delays=[delay_rng(dout_delay, dout_delay)])
    sim(resdir=tmpdir)


@pytest.mark.parametrize('din_delay', [0, 10])
@pytest.mark.parametrize('dout_delay', [0, 10])
def test_qfilt_delay(tmpdir, cosim_cls, din_delay, dout_delay):
    @datagear
    def even(x: Integer) -> Bool:
        return not x[0]

    directed(
        drv(t=Queue[Uint[8]], seq=[list(range(10)), list(range(10))])
        | delay_rng(din_delay, din_delay),
        f=filt(sim_cls=cosim_cls, f=even),
        ref=[list(range(0, 10, 2)), list(range(0, 10, 2))],
        delays=[delay_rng(dout_delay, dout_delay)])

    sim(resdir=tmpdir)


def test_filt_base():
    data_t = Union[Uint[1], Uint[2], Uint[3]]
    data = [data_t(Uint[1](0), 0), data_t(Uint[2](3), 1), data_t(Uint[3](7), 2)]
    sel = [1, 1, 1]

    seq = list(zip(data, sel))
    ref = [data for data, sel in seq if data.ctrl == sel]

    directed(drv(t=Tuple[data_t, Uint[2]], seq=seq), f=filt, ref=ref)
    sim()


@synth_check({'logic luts': 1, 'ffs': 0}, tool='vivado')
def test_filt_synth_vivado():
    filt(Intf(union_din), fixsel=0)


@synth_check({'logic luts': 2, 'ffs': 0}, tool='yosys')
def test_filt_synth_yosys():
    filt(Intf(union_din), fixsel=0)
