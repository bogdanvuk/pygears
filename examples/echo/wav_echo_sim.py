import wav_utils

from echo import echo, stereo_echo
from pygears import gear
from pygears.sim import sim
from pygears.cookbook.verif import drv
from pygears.sim.modules import SimVerilated
from pygears.typing import Tuple, Int, typeof


def wav_echo_sim(ifn,
                 ofn,
                 stereo=True,
                 cosim=True,
                 sample_rng=None,
                 feedback_gain=0.6,
                 delay=0.25):
    """Applies echo effect on a WAV file using Verilator cosimulation

    ifn - Input WAV file name
    ofn - Output WAV file name
    """

    samples_all, params = wav_utils.load_wav(ifn, stereo=stereo)
    samples = samples_all[:sample_rng]

    if stereo:
        sim_func = stereo_echo_sim
    else:
        sim_func = mono_echo_sim

    res = sim_func(
        samples,
        cosim=cosim,
        sample_rate=params.framerate,
        sample_width=params.sampwidth,
        feedback_gain=feedback_gain,
        delay=delay)

    # print(f'Result length: {len(res)}')

    # wav_utils.dump_wav(ofn, res, params, stereo=stereo)

    # try:
    #     wav_utils.plot_wavs(samples, res, stereo=stereo)
    # except:
    #     pass


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
                  cosim=True,
                  feedback_gain=0.5,
                  delay=0.250,
                  stereo=True):
    sample_bit_width = 8 * sample_width

    result = []
    drv(t=Int[sample_bit_width], seq=seq) \
        | echo(feedback_gain=feedback_gain,
               sample_rate=sample_rate,
               delay=delay,
               sim_cls=SimVerilated if cosim else None) \
        | collect(result=result, samples_num=len(seq))

    # sim(outdir='./build')

    return result


def stereo_echo_sim(seq,
                    sample_rate,
                    sample_width,
                    cosim=False,
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
                      sim_cls=SimVerilated if cosim else None) \
        | collect(result=result, samples_num=len(seq))

    sim(outdir='./build')

    return result
