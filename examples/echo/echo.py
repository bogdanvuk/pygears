from pygears import gear, Intf
from pygears.common import fifo, mul, add, const, union_collapse, fmap
from pygears.typing import Int, ceil_pow2, Tuple, typeof
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
def fill_void(din, fill):
    return priority_mux(din, fill) \
        | union_collapse


@gear
def echo(
        din,  # audio samples
        *,
        feedback_gain: float,  # feedback gain == echo gain
        sample_rate: int,  # sample_rate in samples per second
        delay: float,  # delay in seconds
        num_format=(1, 15)):  # 1 for sign, 15 fraction

    #########################
    # Parameter calculation #
    #########################

    sample_dly_len = sample_rate * delay
    fifo_depth = ceil_pow2(sample_dly_len)
    feedback_gain_fixp = Int[16](float_to_fixp(feedback_gain, num_format))

    #########################
    # Hardware description  #
    #########################

    dout = Intf(din.dtype)

    feedback = dout \
        | fifo(depth=fifo_depth, threshold=fifo_depth - 1) \
        | fill_void(fill=Int[16](0))

    feedback_attenuated = (feedback * feedback_gain_fixp) >> num_format[1]

    dout |= (din + feedback_attenuated) | dout.dtype

    return dout


@gear
def stereo_echo(
        din,  # audio samples
        *,
        feedback_gain: float,  # feedback gain == echo gain
        sample_rate: int,  # sample_rate in samples per second
        delay: float,  # delay in seconds
        num_format=(1, 15)):

    mono_echo = echo(
        feedback_gain=feedback_gain,
        sample_rate=sample_rate,
        delay=delay,
        num_format=num_format)

    return din | fmap(f=(mono_echo, mono_echo))


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

        if typeof(din.dtype, Int):
            result.append(int(val))
        else:
            result.append((int(val[0]), int(val[1])))


def echo_sim(seq,
             sample_rate,
             sample_width,
             feedback_gain=0.5,
             delay=0.250,
             mono=False):
    sample_bit_width = 8 * sample_width

    if mono:
        dtype = Int[sample_bit_width]
        echo_func = echo
    else:
        dtype = Tuple[Int[sample_bit_width], Int[sample_bit_width]]
        echo_func = stereo_echo

    result = []
    drv(t=dtype, seq=seq) \
        | echo_func(feedback_gain=feedback_gain,
                    sample_rate=sample_rate,
                    delay=delay,
                    sim_cls=SimVerilated) \
        | collect(result=result, samples_num=len(seq))

    sim(outdir='./build')

    return result
