import os
from wav_echo_sim import wav_echo_sim

wav_echo_sim(
    os.path.join(os.path.dirname(__file__), 'plop.wav'),
    os.path.join('build', 'plop_echo.wav'),
    feedback_gain=0.6,
    delay=0.25,
    stereo=False
)
