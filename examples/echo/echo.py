from pygears import gear, Intf
from pygears.lib import fifo, union_collapse, fmap, decouple, filt
from pygears.typing import Int, ceil_pow2
from pygears.lib import priority_mux


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
        | fifo(depth=fifo_depth, threshold=sample_dly_len, regout=True) \
        | fill_void(fill=din.dtype(0)) \
        | decouple

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
