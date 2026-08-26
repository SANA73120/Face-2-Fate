import os
import json
from video_analysis import analyze_video
from audio_analysis import analyze_audio_wav
from text_analysis import transcribe_audio
from confidence_score import calculate_confidence_score
from utils import get_db, extract_audio_from_video, UPLOAD_FOLDER


def process_video_pipeline(video_path, u_id, q_id, v_id):

    # ================= VIDEO =================
    video_metrics = analyze_video(video_path)
    print(f"[PIPELINE] Video analysis done. Starting audio extraction...")
    
    # ================= AUDIO =================
    audio_filename = f"audio_{u_id}_{q_id}.wav"
    audio_path = os.path.join(UPLOAD_FOLDER, audio_filename)

    extract_audio_from_video(video_path, audio_path)

    audio_metrics = analyze_audio_wav(audio_path)

    # ================= TEXT =================
    text_metrics = transcribe_audio(audio_path)

    # ================= CONFIDENCE SCORE =================
    confidence_result = calculate_confidence_score(
        eye_contact_percent=video_metrics["eye_contact_percent"],
        blink_rate=video_metrics["blink_rate"],
        filler_count=text_metrics["filler_count"],
        duration_sec=audio_metrics["duration_sec"],
        emotion_distribution=video_metrics["emotion_distribution"],
        avg_hand_movement=video_metrics["avg_hand_movement"],
        pitch_variation=audio_metrics["pitch_variation"],
        energy_variation=audio_metrics["energy_variation"]
    )

    score        = confidence_result["confidence_score"]
    breakdown    = confidence_result["breakdown"]
    main_feedback = confidence_result["main_feedback"]

    # ================= DATABASE =================
    db = get_db()
    cursor = db.cursor()

    cursor.execute(
        """
        INSERT INTO video_analysis
        (eye_contact_percent, blink_rate, emotion_distribution, hand_movement, v_id)
        VALUES (%s,%s,%s,%s,%s)
        """,
        (
            float(video_metrics["eye_contact_percent"]),
            float(video_metrics["blink_rate"]),
            json.dumps(video_metrics["emotion_distribution"]),
            float(video_metrics["avg_hand_movement"]),
            v_id
        )
    )

    cursor.execute(
        """
        INSERT INTO audio_analysis
        (duration, energy_var, pitch_var, v_id)
        VALUES (%s,%s,%s,%s)
        """,
        (
            float(audio_metrics["duration_sec"]),
            float(audio_metrics["energy_variation"]),
            float(audio_metrics["pitch_variation"]),
            v_id
        )
    )

    cursor.execute(
        """
        INSERT INTO text_analysis
        (filler_events, filler_count, transcript, v_id)
        VALUES (%s,%s,%s,%s)
        """,
        (
            json.dumps(text_metrics["filler_events"]),
            text_metrics["filler_count"],
            text_metrics["transcript"],
            v_id
        )
    )

    cursor.execute(
        """
        INSERT INTO report (score, breakdown, main_feedback, v_id)
        VALUES (%s,%s,%s,%s)
        """,
        (
            score,
            json.dumps(breakdown),
            main_feedback,
            v_id
        )
    )

    # ================= MARK AS DONE =================
    cursor.execute(
        "UPDATE video SET status='done' WHERE v_id=%s",
        (v_id,)
    )

    db.commit()
    cursor.close()
    db.close()