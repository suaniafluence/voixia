# app/audio_utils.py
"""
Conversion audio entre G.711 μ-law et PCM16 mono.
"""
import numpy as np

def mulaw2linear(data: bytes) -> np.ndarray:
    """
    Convertit un flux de données µ-law (G.711) en tableau PCM16 signé.

    :param data: bytes en µ-law non signées (uint8)
    :return: numpy.ndarray de type int16 (PCM16)
    """
    # Lecture des octets en uint8
    ulaw = np.frombuffer(data, dtype=np.uint8)
    # Conversion µ-law → PCM16 (approximation)
    pcm = ((ulaw.astype(np.int16) - 128) << 8)
    return pcm


def linear2mulaw(pcm_bytes: bytes) -> bytes:
    """
    Convertit un flux PCM16 mono en données µ-law (G.711).

    :param pcm_bytes: bytes représentant des int16 PCM16
    :return: bytes en µ-law (uint8)
    """
    # Lecture du flux PCM en int16
    arr = np.frombuffer(pcm_bytes, dtype=np.int16)
    # Conversion PCM16 → µ-law (approximation)
    ulaw = ((arr >> 8) + 128).astype(np.uint8)
    return ulaw.tobytes()
