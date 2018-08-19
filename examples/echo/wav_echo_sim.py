from pygears.typing import Int
import wav_utils

from echo import echo_sim


def wav_echo_sim_gen(ifn, ofn):
    """Applies echo effect on a WAV file using Verilator cosimulation

    ifn - Input WAV file name
    ofn - Output WAV file name
    """


def wav_echo_sim(ifn, ofn, plot=True, mono=False, sample_rng=None):
    """Applies echo effect on a WAV file using Verilator cosimulation

    ifn - Input WAV file name
    ofn - Output WAV file name
    """

    samples_all, params = wav_utils.load_wav(ifn, mono=mono)
    sample_rng = samples_all[:None]

    res = echo_sim(
        sample_rng,
        sample_rate=params.framerate,
        sample_width=params.sampwidth,
        feedback_gain=0.6,
        delay=0.25,
        mono=mono)

    print(f'Result length: {len(res)}')

    wav_utils.dump_wav(ofn, res, params, mono=mono)

    if plot:
        wav_utils.plot_wavs(sample_rng, res, mono=mono)
