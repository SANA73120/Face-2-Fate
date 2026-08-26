import librosa
import matplotlib.pyplot as plt
from datetime import timedelta
import pandas as pd
import numpy as np

def analyze_audio_wav(wav_path):

    y, sr = librosa.load(wav_path, sr=None, mono=True)

    y = y / np.max(np.abs(y))

    duration_sec = librosa.get_duration(y=y, sr=sr)

    rms = librosa.feature.rms(y=y)[0]

    rms_db = librosa.amplitude_to_db(rms + 1e-10, ref=np.max)

    mean_energy_db = np.mean(rms_db)
    std_energy_db = np.std(rms_db)

    energy_variation = std_energy_db / abs(mean_energy_db)

    f0 = librosa.yin(y,fmin=80,fmax=400,sr=sr)

    pitch = np.nan_to_num(f0)

    valid_pitch = pitch[pitch>0]

    if len(valid_pitch)>0:

        mean_pitch=np.mean(valid_pitch)
        pitch_std=np.std(valid_pitch)
        pitch_variation=pitch_std/mean_pitch

    else:

        mean_pitch=0
        pitch_variation=0

    return {
        "duration_sec": duration_sec,
        "energy_variation": energy_variation,
        "pitch_variation": pitch_variation,
        "pitch_values": pitch,
        "sr": sr
    }