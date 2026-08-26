# video.py
# ============================================================
# Video → Audio → Whisper (WORDS) + Silence Hesitation
# ============================================================

import whisper
import librosa
from moviepy.editor import VideoFileClip

SR = 16000
SILENCE_THRESHOLD = 0.01

# Load Whisper ONCE
_whisper_model = whisper.load_model("small")


# ------------------------------------------------------------
# Extract audio from video
# ------------------------------------------------------------
def extract_audio(video_path, audio_path="audio.wav"):
    video = VideoFileClip(video_path)
    video.audio.write_audiofile(
        audio_path,
        codec="pcm_s16le",
        fps=SR,
        nbytes=2,
        verbose=False,
        logger=None
    )
    video.close()
    return audio_path


# ------------------------------------------------------------
# Whisper transcription (FULL TEXT)
# ------------------------------------------------------------
def whisper_transcribe(audio_path):
    result = _whisper_model.transcribe(
        audio_path,
        language="en",
        fp16=False,
        verbose=False
    )
    return result["text"]


# ------------------------------------------------------------
# Detect silent pauses >= min_pause_sec
# ------------------------------------------------------------
def detect_long_silences(audio_path, min_pause_sec=3.0):
    y, _ = librosa.load(audio_path, sr=SR)

    frame_length = 2048
    hop_length = 512

    rms = librosa.feature.rms(
        y=y,
        frame_length=frame_length,
        hop_length=hop_length
    )[0]

    times = librosa.frames_to_time(
        range(len(rms)),
        sr=SR,
        hop_length=hop_length
    )

    pauses = []
    pause_start = None

    for t, e in zip(times, rms):
        if e < SILENCE_THRESHOLD:
            if pause_start is None:
                pause_start = t
        else:
            if pause_start is not None:
                duration = t - pause_start
                if duration >= min_pause_sec:
                    pauses.append({
                        "start": round(pause_start, 2),
                        "end": round(t, 2),
                        "duration": round(duration, 2)
                    })
                pause_start = None

    # Handle silence at end
    if pause_start is not None:
        duration = times[-1] - pause_start
        if duration >= min_pause_sec:
            pauses.append({
                "start": round(pause_start, 2),
                "end": round(times[-1], 2),
                "duration": round(duration, 2)
            })

    return pauses


# ------------------------------------------------------------
# MAIN FUNCTION (THIS is what app.py should call)
# ------------------------------------------------------------
def process_video(video_path, min_pause_sec=3.0):
    audio_path = extract_audio(video_path)

    transcript = whisper_transcribe(audio_path)
    pauses = detect_long_silences(audio_path, min_pause_sec)

    return {
        "transcript": transcript,
        "pauses": pauses
    }
