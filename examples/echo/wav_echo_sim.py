from pygears.typing import Int
import wav_utils

from echo import echo_sim


def wav_echo_sim_gen(ifn, ofn):
    """Applies echo effect on a WAV file using Verilator cosimulation

    ifn - Input WAV file name
    ofn - Output WAV file name
    """


def wav_echo_sim(ifn, ofn, plot=True, stereo=True, sample_rng=None):
    """Applies echo effect on a WAV file using Verilator cosimulation

    ifn - Input WAV file name
    ofn - Output WAV file name
    """

    samples_all, params = wav_utils.load_wav(ifn, stereo=stereo)
    samples = samples_all[:sample_rng]

    res = echo_sim(
        samples,
        sample_rate=params.framerate,
        sample_width=params.sampwidth,
        feedback_gain=0.6,
        delay=0.25,
        stereo=stereo)

    print(f'Result length: {len(res)}')

    wav_utils.dump_wav(ofn, res, params, stereo=stereo)

    if plot:
        wav_utils.plot_wavs(samples, res, stereo=stereo)
