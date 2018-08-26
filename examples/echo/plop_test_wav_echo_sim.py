from wav_echo_sim import wav_echo_sim

wav_echo_sim(
    'plop.wav',
    'build/plop_echo.wav',
    feedback_gain=0.6,
    delay=0.25,
    stereo=False)
