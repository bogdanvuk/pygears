from pygears import gear, Intf
from pygears.common import fifo, mul, add, const, union_collapse
from pygears.typing import Int, bitw
from pygears.cookbook import shr, priority_mux
from pygears.sim.modules.verilator import SimVerilated
from pygears.sim import sim
from pygears.sim.modules.drv import drv

import scipy.io.wavfile as wav
import numpy as np
import math
import itertools


def float_to_fixp(number, num_format):
    rng = (2**float(num_format[0])) / 2
    number = number / rng
    w_num = sum(num_format)
    number = int(number * 2**(w_num - 1))
    return number


@gear
async def check(din, *, ret):
    val = await din.get()
    ret.append(val)


@gear
def echo(
        din,  # audio samples
        *,
        feedback_gain,  # feedback gain == echo gain
        sample_rate,  # sample_rate in samples per second
        delay,  # delay in seconds
        num_format=(1, 15)):  # 1 for sign, 15 fraction

    dly_len = sample_rate * delay

    feedback_attenuation = Intf(dtype=din.dtype)

    dout = add(din, feedback_attenuation) \
           | din.dtype

    feedback = dout | fifo(depth=2**(bitw(dly_len)), threshold=0)

    shift = const(val=num_format[1])

    feedback_gain_fix = const(
        val=float_to_fixp(feedback_gain, num_format), tout=Int[16])

    feedback_attenuated = (feedback, const(val=0, tout=Int[16])) \
                        | priority_mux \
                        | union_collapse

    feedback_attenuated = mul(feedback_attenuated, feedback_gain_fix)

    feedback_attenuated | shr(cfg=shift, intfs=[feedback_attenuation])

    return dout


###################### Simulation #####################################

dinT = Int[16]  # Input data type
Data_max_val = 2**(len(dinT) - 1)

audio_file = wav.read("436192__arnaud-coutancier__creakings.wav") # path to wav file

stereo_samples = np.array(audio_file[1], dtype=float)  # stereo audio samples
sample_rate = audio_file[0]

mono_seq = [x[0] for x in stereo_samples]  # extract mono sample sequence

scale_coef = math.floor(
    (Data_max_val / max(map(abs, mono_seq))) *  # scale coef for max volume
    1000) / 1000

seq = [scale_coef * x for x in mono_seq]

seq_dirac = (np.zeros(5000), Data_max_val*np.ones(1), np.zeros(150000))
seq_dirac = list(itertools.chain.from_iterable(seq_dirac))

ret = []
drv(t=dinT, seq=seq) \
    | echo(feedback_gain=0.5, sample_rate=sample_rate, delay=0.250, sim_cls=SimVerilated) \
    | check(ret=ret)

sim(outdir='./echo_proba')

ret_scaled = []
for i in range(0, len(ret)):
    ret_scaled.append(float(int(ret[i])) / 2**(len(dinT) - 1))

numpy_ret = np.array(ret_scaled)

wav.write("output.wav", sample_rate, numpy_ret.T)
