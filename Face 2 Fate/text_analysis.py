from groq import Groq
import re
import os
from dotenv import load_dotenv

load_dotenv()


def transcribe_audio(audio_file_path):

    client = Groq(api_key=os.getenv("GROQ_API_KEY"))

    with open(audio_file_path, "rb") as audio_file:

        transcription = client.audio.transcriptions.create(
            file=("interview.wav", audio_file.read()),
            model="whisper-large-v3-turbo",
            response_format="verbose_json",
            language="en",
            timestamp_granularities=["word"],
            prompt=(
                "Transcribe verbatim exactly as spoken, no corrections, smoothing, or removal of anything. "
                "Preserve EVERY filler word (um, uh, er, ah, hmm, like, you know, right, sorta, kinda), "
                "word repetitions, false starts, stutters, hesitations and disfluencies."
            ),
            temperature=0.0
        )

    # ⭐ FULL TRANSCRIPT
    full_transcript = transcription.text

    # ⭐ FILLER DETECTION
    FILLERS = {
        "um", "uh", "er", "ah", "hmm",
        "like", "right", "sorta", "kinda",
        "basically", "actually", "well", "so", "okay"
    }

    filler_events = []

    words_list = transcription.words

    for i, word in enumerate(words_list):

        raw_word = word["word"]
        cleaned = re.sub(r"[^\w]", "", raw_word.lower())

        start = word["start"]
        end = word["end"]

        # single filler
        if cleaned in FILLERS:
            filler_events.append({
                "word": raw_word,
                "start": start,
                "end": end,
                "duration": end - start
            })

        # multi word filler : you know
        if i < len(words_list) - 1:
            next_raw = words_list[i + 1]["word"]
            next_clean = re.sub(r"[^\w]", "", next_raw.lower())

            if cleaned == "you" and next_clean == "know":
                filler_events.append({
                    "word": "you know",
                    "start": start,
                    "end": words_list[i + 1]["end"],
                    "duration": words_list[i + 1]["end"] - start
                })

    total_filler_count = len(filler_events)

    return {
        "transcript": full_transcript,
        "filler_events": filler_events,
        "filler_count": total_filler_count
    }