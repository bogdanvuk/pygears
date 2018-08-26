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


def float_to_fixp(number, precision, sample_width):
    rng = (2**float(sample_width - precision)) / 2
    number = number / rng
    number = int(number * 2**(sample_width - 1))
    return number


@gear
def fill_void(din, fill):
    return priority_mux(din, fill) \
        | union_collapse


@gear
def echo(din: Int['W'],
         *,
         feedback_gain,
         sample_rate,
         delay,
         precision=15,
         sample_width=b'W'):
    """Performs echo audio effect on the continuous input sample stream

    Args:
        din: Stream of audio samples

    Keyword Args:
        feedback_gain (float): gain of the feedback loop
        sample_rate (int): samples per second
        delay (float): delay in seconds
        precision (int): sample fixed point precision
        sample_width (int): sample width in bits

    Returns:
        - **dout** - Stream of audio samples with applied echo

    """

    #########################
    # Parameter calculation #
    #########################

    sample_dly_len = sample_rate * delay
    fifo_depth = ceil_pow2(sample_dly_len)
    feedback_gain_fixp = din.dtype(
        float_to_fixp(feedback_gain, precision, sample_width))

    #########################
    # Hardware description  #
    #########################

    dout = Intf(din.dtype)

    feedback = dout \
        | fifo(depth=fifo_depth, threshold=sample_dly_len) \
        | fill_void(fill=din.dtype(0))

    feedback_attenuated = (feedback * feedback_gain_fixp) >> precision

    dout |= (din + feedback_attenuated) | dout.dtype

    return dout


@gear
def stereo_echo(
        din,  # audio samples
        *,
        feedback_gain,  # feedback gain == echo gain
        sample_rate,  # sample_rate in samples per second
        delay,  # delay in seconds
        precision=15):

    mono_echo = echo(
        feedback_gain=feedback_gain,
        sample_rate=sample_rate,
        delay=delay,
        precision=precision)

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


def mono_echo_sim(seq,
                  sample_rate,
                  sample_width,
                  feedback_gain=0.5,
                  delay=0.250,
                  stereo=True,
                  verilator_cosim=False):
    sample_bit_width = 8 * sample_width

    result = []
    drv(t=Int[sample_bit_width], seq=seq) \
        | echo(feedback_gain=feedback_gain,
               sample_rate=sample_rate,
               delay=delay,
               sim_cls=SimVerilated) \
        | collect(result=result, samples_num=len(seq))

    sim(outdir='./build')

    return result


def stereo_echo_sim(seq,
                    sample_rate,
                    sample_width,
                    feedback_gain=0.5,
                    delay=0.250,
                    stereo=True,
                    verilator_cosim=False):
    sample_bit_width = 8 * sample_width

    result = []
    drv(t=Tuple[Int[sample_bit_width], Int[sample_bit_width]], seq=seq) \
        | stereo_echo(feedback_gain=feedback_gain,
                      sample_rate=sample_rate,
                      delay=delay,
                      sim_cls=SimVerilated) \
        | collect(result=result, samples_num=len(seq))

    sim(outdir='./build')

    return result
