from pygears import gear, Intf
from pygears.common import fifo, mul, add, const, union_collapse
from pygears.typing import Int, bitw
from pygears.cookbook import shr, priority_mux

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

    dly_len = sample_rate * delay

    feedback_attenuation = Intf(dtype=din.dtype)

    dout = add(din, feedback_attenuation) \
        | din.dtype

    feedback = dout | fifo(
        depth=2**(bitw(dly_len)), threshold=2**(bitw(dly_len)) - 1)

    shift = const(val=num_format[1])

    feedback_gain_fix = const(
        val=float_to_fixp(feedback_gain, num_format), tout=Int[16])

    feedback_attenuated = priority_mux(feedback, Int[16](0)) \
        | union_collapse

    feedback_attenuated = mul(feedback_attenuated, feedback_gain_fix)

    feedback_attenuated | shr(cfg=shift, intfs=[feedback_attenuation])

    return dout
