import os
import pytest
from pygears import Intf, config, gear, sim
from pygears.rtl import rtlgen
from pygears.typing import Uint
from pygears.sim.modules import SimVerilated
from pygears.cookbook.verif import directed, drv
from pygears.core.gear import InSig, OutSig


@pytest.fixture(autouse=True)
def configure():
    config['svgen/sv_paths'].append(
        os.path.join(os.path.dirname(__file__), 'test_signals'))


@gear(signals=[OutSig('dout_sig', 16)])
def bc_sig(din) -> b'din':
    pass


@gear(signals=[InSig('din_sig', 16)])
def add_sig(din) -> b'din':
    pass


def test_local_signal(tmpdir):
    @gear
    def dut(din):
        return din \
            | bc_sig(sigmap={'dout_sig': 'sig'}) \
            | add_sig(sigmap={'din_sig': 'sig'})

    directed(drv(t=Uint[16], seq=list(range(3))),
             f=dut(sim_cls=SimVerilated),
             ref=(list(range(0, 6, 2))))

    sim(outdir=tmpdir)


@gear
def add_wrap(din):
    return din | add_sig


def test_channeling(tmpdir):
    @gear
    def dut(din):
        return din \
            | bc_sig(sigmap={'dout_sig': 'sig'}) \
            | add_wrap(sigmap={'din_sig': 'sig'})

    directed(drv(t=Uint[16], seq=list(range(3))),
             f=dut(sim_cls=SimVerilated),
             ref=(list(range(0, 6, 2))))

    sim(outdir=tmpdir)


@gear(signals=[InSig('clk', 1), InSig('rst', 1), InSig('clk2', 1)])
def gear_clk2(din):
    pass


def test_clk_channeling():
    @gear
    def dut(din):
        return din \
            | gear_clk2

    Intf(Uint[16]) | dut

    rtltop = rtlgen()

    assert InSig('clk2', 1) in rtltop['/dut'].params['signals']


# config['svgen/sv_paths'].append(
#     os.path.join(os.path.dirname(__file__), 'test_signals'))
# test_channeling('/tools/home/tmp')
