import wave
import audioop
import array


def load_wav(fn, mono=False):

    with wave.open(fn, mode='rb') as audio_file:
        params = audio_file.getparams()

        print(f'''Audio file "{fn}":

    Channels     : {params.nchannels}
    Framerate    : {params.framerate}
    Sample width : {params.sampwidth} Bytes
    Sample num   : {params.nframes}
''')

        sample_bytes = audio_file.readframes(params.nframes)

        if mono:
            sample_bytes = audioop.tomono(sample_bytes, params.sampwidth, 1, 0)

        samples = [
            audioop.getsample(sample_bytes, params.sampwidth, i)
            for i in range(params.nframes)
        ]

    return samples, params


def dump_wav(fn, samples, params, mono=False):
    with wave.open(fn, mode='wb') as audio_file:
        sample_bytes = array.array('h', samples)

        if mono:
            sample_bytes = audioop.tostereo(sample_bytes, params.sampwidth, 1,
                                            0)

        audio_file.setparams(params)
        audio_file.writeframesraw(sample_bytes)


def plot_wavs(*wavs):
    try:
        import matplotlib.pyplot as plt
    except:
        pass

    f, axarr = plt.subplots(len(wavs), sharex=True)
    for ax, wav in zip(axarr, wavs):
        ax.plot(wav)

    plt.show()
