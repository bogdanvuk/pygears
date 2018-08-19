from pygears import gear, Intf
from pygears.common import fifo, mul, add, const, union_collapse
from pygears.typing import Int, ceil_pow2
from pygears.cookbook import priority_mux

from pygears import gear
from pygears.typing import Int

from pygears.sim.modules.verilator import SimVerilated
from pygears.sim import sim
from pygears.sim.modules.drv import drv

# Provide WAV file and path to wav.read(),
# COMMENT spy interface in DTI.sv in order for this test to work.


def float_to_fixp(number, num_format):
    rng = (2**float(num_format[0])) / 2
    number = number / rng
    w_num = sum(num_format)
    number = int(number * 2**(w_num - 1))
    return number


@gear
def echo(
        din,  # audio samples
        *,
        feedback_gain,  # feedback gain == echo gain
        sample_rate,  # sample_rate in samples per second
        delay,  # delay in seconds
        num_format=(1, 15)):  # 1 for sign, 15 fraction

    # Parameter calculation

    dly_len = sample_rate * delay
    fifo_depth = ceil_pow2(dly_len)
    feedback_gain_fixp = Int[16](float_to_fixp(feedback_gain, num_format))

    # Hardware description

    feedback_attenuation = Intf(dtype=din.dtype)

    dout = add(din, feedback_attenuation) \
        | din.dtype

    feedback = dout | fifo(depth=fifo_depth, threshold=fifo_depth - 1)

    feedback = priority_mux(feedback, Int[16](0)) \
        | union_collapse \

    (feedback * feedback_gain_fixp >> num_format[1]) \
        @ feedback_attenuation

    return dout


@gear
async def collect(din, *, result, samples_num):
    async with din as val:
        if len(result) % 10 == 0:
            if samples_num is not None:
                print(
                    f"Calculated {len(result)}/{samples_num} samples",
                    end='\r')
            else:
                print(f"Calculated {len(result)} samples", end='\r')

        result.append(val)


def echo_sim(seq, sample_rate, feedback_gain=0.5, delay=0.250, dtype=Int[16]):
    result = []
    drv(t=dtype, seq=seq) \
        | echo(feedback_gain=feedback_gain,
               sample_rate=sample_rate,
               delay=delay,
               sim_cls=SimVerilated) \
        | collect(result=result, samples_num=len(seq))

    sim(outdir='./build')

    return result
