# tests/test_audio_utils.py
import numpy as np
from app.audio_utils import mulaw2linear, linear2mulaw

def test_roundtrip():
    pcm = np.array([0, 32767, -32768], dtype=np.int16)
    mu = linear2mulaw(pcm.tobytes())
    pcm2 = mulaw2linear(mu)
    assert isinstance(pcm2, np.ndarray)
    assert pcm2.shape == pcm.shape