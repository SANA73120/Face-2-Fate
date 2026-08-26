import os
import requests
from groq import Groq
from dotenv import load_dotenv

load_dotenv()


def get_eye_contact_feedback(score):
    if score < 40:
        return "Eye contact was limited at times. Try looking toward the camera more consistently to convey confidence and engagement."
    elif score < 60:
        return "Eye contact was somewhat inconsistent. Maintaining a steadier gaze can help strengthen your overall presence."
    elif score < 80:
        return "Good eye contact overall. You appeared attentive and reasonably confident during your responses."
    else:
        return "Excellent eye contact. You projected strong confidence and maintained clear engagement throughout."


def get_blink_rate_feedback(score):
    if score < 40:
        return "Blink frequency appeared slightly high, which can naturally happen under pressure. Taking calm pauses may help you feel more composed."
    elif score < 70:
        return "Blink rate was mildly elevated. Slowing your pace and focusing on steady breathing can improve relaxation."
    elif score < 90:
        return "Blink rate was within a focused and natural range, suggesting steady concentration."
    else:
        return "Very natural blink behaviour. You appeared calm, relaxed, and self-assured."


def get_filler_feedback(score):
    if score < 40:
        return "Frequent filler words were noticed. Practicing structured responses and using brief silent pauses can improve clarity and confidence."
    elif score < 60:
        return "Some filler usage was present. With more preparation and pacing, your delivery can become smoother."
    elif score < 80:
        return "Minor filler usage detected. Overall speech flow was fairly natural with only occasional hesitation."
    else:
        return "Speech was clear and fluent with minimal fillers. You communicated your ideas confidently."


def get_emotion_feedback(score):
    if score < 30:
        return "Expressions appeared slightly tense. Relaxing facial muscles and adding occasional smiles can improve approachability."
    elif score < 55:
        return "Expressions were mostly neutral or serious. A warmer expression can help build better connection with the interviewer."
    elif score < 75:
        return "Facial expressions were calm and composed for most of the interaction."
    else:
        return "Positive and engaging expressions throughout. You appeared enthusiastic and approachable."


def get_pitch_feedback(pitch_variation):
    if pitch_variation < 0.1:
        return "Delivery sounded quite monotone. Varying your tone more naturally can make your responses feel more engaging."
    elif pitch_variation < 0.2:
        return "Pitch was slightly flat at times. Adding more tonal variation can help keep the listener engaged."
    elif pitch_variation <= 0.35:
        return "Good pitch variation throughout. Your tone sounded natural and easy to follow."
    else:
        return "Very expressive pitch detected. Try to keep tonal shifts controlled and purposeful."


def get_energy_feedback(energy_variation):
    if energy_variation < 0.3:
        return "Speech energy was quite flat. Adding more vocal emphasis on key points can improve impact."
    elif energy_variation < 0.6:
        return "Moderate vocal energy detected. You were reasonably engaging with some room to add more emphasis."
    elif energy_variation <= 0.9:
        return "Good vocal energy throughout. You sounded dynamic and held attention well."
    else:
        return "Energy levels varied significantly. Try to maintain a more consistent vocal presence."


def generate_main_feedback_groq(
    eye_contact_percent,
    blink_rate,
    filler_count,
    duration_sec,
    emotion_distribution,
    avg_hand_movement,
    pitch_variation,
    energy_variation,
    confidence_score
):

    # ===== BUILD DOMINANT EMOTION STRING =====
    if emotion_distribution:
        dominant_emotion = max(emotion_distribution, key=emotion_distribution.get)
        emotion_str = ", ".join(
            f"{k}: {round(v*100, 1)}%" for k, v in emotion_distribution.items()
        )
    else:
        dominant_emotion = "neutral"
        emotion_str = "neutral: 100%"

    prompt = f"""You are an expert interview coach. A candidate just completed a mock interview.
Based on the analysis below, write a 3-4 sentence overall feedback summary.
Be specific, encouraging but honest. Do not use bullet points. Just plain sentences.

Interview Analysis:
- Confidence Score: {confidence_score} / 100
- Eye Contact: {round(eye_contact_percent, 1)}%
- Blink Rate: {round(blink_rate, 1)} blinks/min
- Hand Movement: {round(avg_hand_movement, 5)}
- Emotion Distribution: {emotion_str} (dominant: {dominant_emotion})
- Pitch Variation: {round(pitch_variation, 4)}
- Energy Variation: {round(energy_variation, 4)}
- Filler Words: {filler_count} in {round(duration_sec, 1)} seconds

Write only the feedback, nothing else. No labels, no intro, just the feedback text."""

    try:
        client = Groq(api_key=os.getenv("GROQ_API_KEY"))

        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            temperature=0.7,
            max_tokens=200
        )

        feedback = response.choices[0].message.content.strip()

        if feedback:
            return feedback

    except Exception as e:
        print(f"[GROQ ERROR] {e}")

    # ===== FALLBACK IF GROQ FAILS =====
    return "Your interview response has been analyzed. Review the individual feedback sections below for detailed insights on your performance."


def calculate_confidence_score(
    eye_contact_percent,
    blink_rate,
    filler_count,
    duration_sec,
    emotion_distribution,
    avg_hand_movement,
    pitch_variation=0,
    energy_variation=0
):

    # ============================================================
    # 1. EYE CONTACT SCORE (30%)
    # ============================================================

    ec = eye_contact_percent

    if ec < 50:
        eye_score = (ec / 50) * 50
    elif ec <= 70:
        eye_score = 50 + ((ec - 50) / 20) * 20
    elif ec <= 85:
        eye_score = 70 + ((ec - 70) / 15) * 30
    else:
        eye_score = 100 - ((ec - 85) / 15) * 20

    eye_score = max(0, min(100, eye_score))

    # ============================================================
    # 2. BLINK RATE SCORE (20%)
    # ============================================================

    br = blink_rate

    if br < 10:
        blink_score = (br / 10) * 70
    elif br <= 20:
        blink_score = 100
    elif br <= 30:
        blink_score = 100 - ((br - 20) / 10) * 30
    else:
        blink_score = max(0, 70 - ((br - 30) / 20) * 70)

    blink_score = max(0, min(100, blink_score))

    # ============================================================
    # 3. FILLER RATIO SCORE (20%)
    # ============================================================

    if duration_sec > 0:
        filler_time = filler_count * 0.4
        filler_ratio = (filler_time / duration_sec) * 100
    else:
        filler_ratio = 0

    if filler_ratio < 2:
        filler_score = 100
    elif filler_ratio <= 6:
        filler_score = 100 - ((filler_ratio - 2) / 4) * 40
    elif filler_ratio <= 8:
        filler_score = 60 - ((filler_ratio - 6) / 2) * 20
    else:
        filler_score = max(0, 40 - ((filler_ratio - 8) / 8) * 40)

    filler_score = max(0, min(100, filler_score))

    # ============================================================
    # 4. EMOTION SCORE (20%)
    # ============================================================

    positive = emotion_distribution.get("happy", 0) + emotion_distribution.get("neutral", 0)
    negative = emotion_distribution.get("sad", 0) + emotion_distribution.get("fear", 0) + emotion_distribution.get("angry", 0)

    emotion_score = (positive * 100) - (negative * 30)
    emotion_score = max(0, min(100, emotion_score))

    # ============================================================
    # 5. HAND MOVEMENT SCORE (10%)
    # ============================================================

    hm = avg_hand_movement

    if hm < 0.001:
        hand_score = 40
    elif hm <= 0.005:
        hand_score = 40 + ((hm - 0.001) / 0.004) * 60
    elif hm <= 0.015:
        hand_score = 100
    elif hm <= 0.03:
        hand_score = 100 - ((hm - 0.015) / 0.015) * 40
    else:
        hand_score = max(0, 60 - ((hm - 0.03) / 0.03) * 60)

    hand_score = max(0, min(100, hand_score))

    # ============================================================
    # WEIGHTED FINAL SCORE
    # ============================================================

    final_score = (
        eye_score     * 0.30 +
        blink_score   * 0.20 +
        filler_score  * 0.20 +
        emotion_score * 0.20 +
        hand_score    * 0.10
    )

    final_score = round(final_score, 2)

    # ============================================================
    # BREAKDOWN WITH FEEDBACK
    # ============================================================

    breakdown = {
        "eye_contact": {
            "score": round(eye_score, 2),
            "feedback": get_eye_contact_feedback(eye_score)
        },
        "blink_rate": {
            "score": round(blink_score, 2),
            "feedback": get_blink_rate_feedback(blink_score)
        },
        "filler": {
            "score": round(filler_score, 2),
            "feedback": get_filler_feedback(filler_score)
        },
        "emotion": {
            "score": round(emotion_score, 2),
            "feedback": get_emotion_feedback(emotion_score)
        },
        "hand_movement": {
            "score": round(hand_score, 2)
        },
        "pitch": {
            "feedback": get_pitch_feedback(pitch_variation)
        },
        "energy": {
            "feedback": get_energy_feedback(energy_variation)
        }
    }

    # ============================================================
    # GROQ MAIN FEEDBACK
    # ============================================================

    main_feedback = generate_main_feedback_groq(
        eye_contact_percent=eye_contact_percent,
        blink_rate=blink_rate,
        filler_count=filler_count,
        duration_sec=duration_sec,
        emotion_distribution=emotion_distribution,
        avg_hand_movement=avg_hand_movement,
        pitch_variation=pitch_variation,
        energy_variation=energy_variation,
        confidence_score=final_score
    )

    return {
        "confidence_score": final_score,
        "breakdown": breakdown,
        "main_feedback": main_feedback
    }