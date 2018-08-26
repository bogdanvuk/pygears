import wav_utils

from echo import mono_echo_sim, stereo_echo_sim


def wav_echo_sim(ifn,
                 ofn,
                 stereo=True,
                 sample_rng=None,
                 feedback_gain=0.6,
                 delay=0.25,
                 verilator_cosim=True):
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
        sample_rate=params.framerate,
        sample_width=params.sampwidth,
        feedback_gain=feedback_gain,
        delay=delay,
        verilator_cosim=verilator_cosim)

    print(f'Result length: {len(res)}')

    wav_utils.dump_wav(ofn, res, params, stereo=stereo)

    try:
        wav_utils.plot_wavs(samples, res, stereo=stereo)
    except:
        pass
