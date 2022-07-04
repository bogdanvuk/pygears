import pytest
from pygears import gear, find, reg, Intf
from pygears.lib import qrange, directed, drv, dreg, add, delay_rng, mul, decouple
from pygears.sim import sim, cosim
from pygears.typing import Uint, Tuple
from pygears.hdl import hdlgen
from pygears.util.test_utils import synth_check


@pytest.mark.parametrize('din_delay', [0, 5])
@pytest.mark.parametrize('dout_delay', [0, 5])
# @pytest.mark.parametrize('din_delay', [0])
# @pytest.mark.parametrize('dout_delay', [0])
def test_basic(din_delay, dout_delay):
    # reg['debug/trace'] = ['*']
    # reg['logger/sim/error'] = 'pass'

    @gear(hdl={'fixed_latency': 2})
    def add_latency_2(din):
        return din | dreg | add | dreg

    directed(drv(t=Tuple[Uint[4], Uint[4]], seq=[(i, i) for i in range(10)])
             | delay_rng(din_delay, din_delay),
             f=add_latency_2,
             ref=[2 * i for i in range(10)],
             delays=[delay_rng(dout_delay, dout_delay)])

    # hdlgen('/add_latency_2', outdir='/tmp/add_latency_2', copy_files=True)

    cosim('/add_latency_2', 'verilator', lang='sv')
    sim()


@synth_check({'logic luts': 10, 'lutrams': 24.0, 'ffs': 8, 'dsp48 blocks': 1.0}, tool='vivado')
def test_basic_synth():
    @gear(hdl={'fixed_latency': 2})
    def add_latency_2(din):
        return din | dreg | mul | dreg

    Intf(Tuple[Uint[16], Uint[16]]) | add_latency_2


# @synth_check({'logic luts': 10, 'lutrams': 24.0, 'ffs': 8, 'dsp48 blocks': 1.0}, tool='vivado')
# def test_basic_synth_regular():
#     @gear(hdl={'fixed_latency': 4})
#     def add_latency_2(din):
#         return din | dreg | dreg | mul | dreg | dreg

#     @gear
#     def top(din):
#         return din | decouple | add_latency_2 | decouple

#     Intf(Tuple[Uint[16], Uint[16]]) | top

@synth_check({'logic luts': 14, 'lutrams': 24.0, 'ffs': 9, 'dsp48 blocks': 1.0}, tool='vivado')
def test_basic_synth_latency_4():
    @gear(hdl={'fixed_latency': 4})
    def add_latency_2(din):
        return din | dreg | dreg | mul | dreg | dreg

    Intf(Tuple[Uint[16], Uint[16]]) | add_latency_2
