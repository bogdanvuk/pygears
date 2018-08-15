from pygears.typing import Int
# import scipy.io.wavfile as wav
import array
import wave
import audioop
import numpy as np
import math
import itertools

from echo_sim import echo_sim


def wav_echo_sim_gen(ifn, ofn):
    """Applies echo effect on a WAV file using Verilator cosimulation

    ifn - Input WAV file name
    ofn - Output WAV file name
    """
    pass


# def byte_sample_to_tuple():
#     pass


def wav_echo_sim(ifn, ofn, plot=True):
    """Applies echo effect on a WAV file using Verilator cosimulation

    ifn - Input WAV file name
    ofn - Output WAV file name
    """

    with wave.open(ifn, mode='rb') as audio_file:
        params = audio_file.getparams()

        print(f'''Audio file "{ifn}":

    Channels     : {params.nchannels}
    Framerate    : {params.framerate}
    Sample width : {params.sampwidth} Bytes
    Sample num   : {params.nframes}
''')

        dtype = Int[8 * params.sampwidth]

        stereo_bytes = audio_file.readframes(params.nframes)

        mono_bytes = audioop.tomono(stereo_bytes, params.sampwidth, 1, 0)

        mono_samples = [
            audioop.getsample(mono_bytes, params.sampwidth, i)
            for i in range(params.nframes)
        ]

        # data_max_val = 2**(len(dtype) - 1)
        # scale_coef = math.floor((data_max_val / max(map(abs, mono_samples)))
        #                         *  # scale coef for max volume
        #                         1000) / 1000

        # seq = [scale_coef * x for x in mono_samples]

    seq = mono_samples

    res = echo_sim(
        seq, params.framerate, dtype=dtype, feedback_gain=0.6, delay=0.25)
    print(f'Result length: {len(res)}')

    res_int = [int(r) for r in res]

    with wave.open(ofn, mode='wb') as audio_file:
        mono_bytes = array.array('h', res_int)

        stereo_bytes = audioop.tostereo(mono_bytes, params.sampwidth, 1, 0)

        audio_file.setparams(params)
        audio_file.writeframesraw(stereo_bytes)

    if plot:
        try:
            import matplotlib.pyplot as plt
            f, axarr = plt.subplots(2, sharex=True)
            axarr[0].plot(seq)
            axarr[1].plot(res_int)
            plt.show()
        except:
            pass
