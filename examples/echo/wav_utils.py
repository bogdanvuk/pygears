import wave
import audioop
import array


def list_samples(sample_bytes, params):
    return [
        audioop.getsample(sample_bytes, params.sampwidth, i)
        for i in range(params.nframes)
    ]


def load_wav(fn, stereo=True):

    with wave.open(fn, mode='rb') as audio_file:
        params = audio_file.getparams()

        print(f'''Audio file "{fn}":

    Channels     : {params.nchannels}
    Framerate    : {params.framerate}
    Sample width : {params.sampwidth} Bytes
    Sample num   : {params.nframes}
''')

        sample_bytes = audio_file.readframes(params.nframes)

        ch_left = audioop.tomono(sample_bytes, params.sampwidth, 1, 0)

        if stereo:
            ch_right = audioop.tomono(sample_bytes, params.sampwidth, 0, 1)
            samples = [(l, r) for l, r in zip(
                list_samples(ch_left, params), list_samples(ch_right, params))]
        else:
            samples = list_samples(ch_left, params)

    return samples, params


def dump_wav(fn, samples, params, stereo=True):
    with wave.open(fn, mode='wb') as audio_file:

        audio_file.setparams(params)

        if stereo:
            audio_file.setnchannels(2)

            ch_left, ch_right = list(zip(*samples))

            left_bytes = audioop.tostereo(
                array.array('h', ch_left), params.sampwidth, 1, 0)

            right_bytes = audioop.tostereo(
                array.array('h', ch_right), params.sampwidth, 0, 1)

            sample_bytes = audioop.add(left_bytes, right_bytes,
                                       params.sampwidth)
        else:
            audio_file.setnchannels(1)
            sample_bytes = array.array('h', samples)

        audio_file.writeframesraw(sample_bytes)


def plot_wavs(*wavs, stereo=True):
    import matplotlib.pyplot as plt

    if stereo:
        stereo_wavs = wavs
        wavs = []
        for wav in stereo_wavs:
            wavs.extend(zip(*wav))

        labels = ['original left', 'original right', 'echo left', 'echo right']

    else:
        labels = ['original', 'echo']

    f, axarr = plt.subplots(len(wavs), sharex=True)
    for ax, wav, lab in zip(axarr, wavs, labels):
        ax.plot(wav)
        ax.set_ylabel(lab)

    plt.show()
