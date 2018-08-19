from pygears.typing import Int
import wav_utils

from echo import echo_sim


def wav_echo_sim_gen(ifn, ofn):
    """Applies echo effect on a WAV file using Verilator cosimulation

    ifn - Input WAV file name
    ofn - Output WAV file name
    """


def wav_echo_sim(ifn, ofn, plot=True):
    """Applies echo effect on a WAV file using Verilator cosimulation

    ifn - Input WAV file name
    ofn - Output WAV file name
    """

    samples, params = wav_utils.load_wav(ifn, mono=True)
    samples = samples[:20000]
    dtype = Int[8 * params.sampwidth]

    res = echo_sim(
        samples, params.framerate, dtype=dtype, feedback_gain=0.6, delay=0.15)
    print(f'Result length: {len(res)}')

    res_int = [int(r) for r in res]

    wav_utils.dump_wav(ofn, res_int, params, mono=True)

    if plot:
        wav_utils.plot_wavs(samples, res_int)
