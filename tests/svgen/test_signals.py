import os
import pytest
from pygears import gear, config, TraceLevel, sim
from pygears.typing import Uint
from pygears.sim.modules import drv, SimVerilated
from pygears.cookbook.verif import check, directed
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


@gear
def dut(din):
    return din \
        | bc_sig(sigmap={'dout_sig': 'sig'}) \
        | add_sig(sigmap={'din_sig': 'sig'})


def test_local_signal(tmpdir):
    directed(drv(t=Uint[16], seq=list(range(3))),
             f=dut(sim_cls=SimVerilated),
             ref=(list(range(0, 6, 2))))

    sim(outdir=tmpdir)
