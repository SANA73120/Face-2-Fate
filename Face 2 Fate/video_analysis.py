import ssl
ssl._create_default_https_context = ssl._create_unverified_context

import cv2
import numpy as np
import pandas as pd
import mediapipe as mp
from collections import Counter
from hsemotion_onnx.facial_emotions import HSEmotionRecognizer

# -------- MEDIAPIPE TASK IMPORT --------
from mediapipe.tasks import python
from mediapipe.tasks.python import vision


# -------- LOAD MODELS --------
base_face = python.BaseOptions(model_asset_path="face_landmarker.task")

face_options = vision.FaceLandmarkerOptions(
    base_options=base_face,
    running_mode=vision.RunningMode.VIDEO
)

base_hand = python.BaseOptions(model_asset_path="hand_landmarker.task")

hand_options = vision.HandLandmarkerOptions(
    base_options=base_hand,
    running_mode=vision.RunningMode.VIDEO
)

# -------- LOAD HSEMOTION --------
emotion_recognizer = HSEmotionRecognizer(model_name="enet_b0_8_best_afew")


def analyze_video(video_path, frame_skip=5):

    cap = cv2.VideoCapture(video_path)

    if not cap.isOpened():
        print("Error: Cannot open video file")
        return

    fps = cap.get(cv2.CAP_PROP_FPS)

    face_landmarker = vision.FaceLandmarker.create_from_options(face_options)
    hand_landmarker = vision.HandLandmarker.create_from_options(hand_options)

    timestamps = []
    eye_contact_list = []
    dominant_emotions = []
    hand_movement_scores = []

    blink_count = 0
    consecutive_closed_frames = 0
    MIN_CLOSED_FRAMES = 2

    EAR_values_initial = []
    EAR_THRESHOLD = None
    calibration_frames = int(fps * 2)

    previous_hand_centers = None
    frame_idx = 0

    while cap.isOpened():

        ret, frame = cap.read()
        if not ret:
            break

        frame_idx += 1
        current_sec = frame_idx / fps
        timestamp_ms = int(current_sec * 1000)

        mp_image = mp.Image(
            image_format=mp.ImageFormat.SRGB,
            data=cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        )

        face_results = face_landmarker.detect_for_video(mp_image, timestamp_ms)

        eye_contact = False

        if face_results.face_landmarks:

            landmarks = face_results.face_landmarks[0]
            h, w, _ = frame.shape

            def euclidean(p1, p2):
                return np.sqrt((p1.x - p2.x)**2 + (p1.y - p2.y)**2)

            left_vertical  = euclidean(landmarks[159], landmarks[145])
            left_horizontal = euclidean(landmarks[33],  landmarks[133])

            right_vertical  = euclidean(landmarks[386], landmarks[374])
            right_horizontal = euclidean(landmarks[362], landmarks[263])

            EAR = (
                (left_vertical  / (left_horizontal  + 1e-6)) +
                (right_vertical / (right_horizontal + 1e-6))
            ) / 2

            if frame_idx <= calibration_frames:
                EAR_values_initial.append(EAR)
                if frame_idx == calibration_frames:
                    open_eye_avg = np.mean(EAR_values_initial)
                    EAR_THRESHOLD = open_eye_avg * 0.75

            if EAR_THRESHOLD is not None:
                if EAR < EAR_THRESHOLD:
                    consecutive_closed_frames += 1
                else:
                    if consecutive_closed_frames >= MIN_CLOSED_FRAMES:
                        blink_count += 1
                    consecutive_closed_frames = 0

            if frame_idx % frame_skip != 0:
                continue

            # ===== HEAD POSE =====
            image_points = np.array([
                (landmarks[1].x   * w, landmarks[1].y   * h),
                (landmarks[33].x  * w, landmarks[33].y  * h),
                (landmarks[263].x * w, landmarks[263].y * h),
                (landmarks[61].x  * w, landmarks[61].y  * h),
                (landmarks[291].x * w, landmarks[291].y * h),
                (landmarks[152].x * w, landmarks[152].y * h)
            ], dtype="double")

            model_points = np.array([
                (0.0,   0.0,  0.0),
                (-30.0, -30.0, -30.0),
                (30.0,  -30.0, -30.0),
                (-25.0,  30.0, -30.0),
                (25.0,   30.0, -30.0),
                (0.0,   60.0, -30.0)
            ])

            focal_length = w
            center = (w / 2, h / 2)

            camera_matrix = np.array(
                [[focal_length, 0, center[0]],
                 [0, focal_length, center[1]],
                 [0, 0, 1]], dtype="double"
            )

            dist_coeffs = np.zeros((4, 1))

            try:
                success, rotation_vector, translation_vector = cv2.solvePnP(
                    model_points,
                    image_points,
                    camera_matrix,
                    dist_coeffs,
                    flags=cv2.SOLVEPNP_ITERATIVE
                )
                rmat, _ = cv2.Rodrigues(rotation_vector)
                angles, _, _, _, _, _ = cv2.RQDecomp3x3(rmat)
                pitch, yaw, roll = angles
            except:
                pitch, yaw = 999, 999

            try:
                left_iris  = landmarks[468]
                right_iris = landmarks[473]
                iris_center_x = (left_iris.x + right_iris.x) / 2
            except:
                iris_center_x = 0

            if abs(yaw) < 18 and abs(pitch) < 18:
                if 0.43 < iris_center_x < 0.57:
                    eye_contact = True

            # ===== HSEMOTION EMOTION DETECTION =====
            # ⭐ get face bounding box from mediapipe landmarks
            try:
                xs = [lm.x * w for lm in landmarks]
                ys = [lm.y * h for lm in landmarks]

                x1 = max(0, int(min(xs)) - 10)
                y1 = max(0, int(min(ys)) - 10)
                x2 = min(w, int(max(xs)) + 10)
                y2 = min(h, int(max(ys)) + 10)

                face_crop = frame[y1:y2, x1:x2]

                if face_crop.size > 0:
                    emotion, scores = emotion_recognizer.predict_emotions(
                        face_crop,
                        logits=False
                    )
                    dominant_emotions.append(emotion.lower())

            except:
                pass

        if frame_idx % frame_skip == 0:

            timestamps.append(current_sec)
            eye_contact_list.append(eye_contact)

            hand_results = hand_landmarker.detect_for_video(mp_image, timestamp_ms)

            movement_score = 0

            if hand_results.hand_landmarks:

                current_centers = []

                for hand in hand_results.hand_landmarks:
                    xs = [lm.x for lm in hand]
                    ys = [lm.y for lm in hand]
                    current_centers.append((np.mean(xs), np.mean(ys)))

                if previous_hand_centers:
                    for (cx, cy), (px, py) in zip(current_centers, previous_hand_centers):
                        movement_score += np.sqrt((cx - px)**2 + (cy - py)**2)

                previous_hand_centers = current_centers

            hand_movement_scores.append(movement_score)

    cap.release()
    face_landmarker.close()
    hand_landmarker.close()

    if not timestamps:
        return None

    video_duration = timestamps[-1]

    blink_rate = (blink_count / video_duration) * 60 if video_duration > 0 else 0

    eye_contact_percent = (sum(eye_contact_list) / len(eye_contact_list)) * 100

    # ⭐ EMOTION DISTRIBUTION AS NORMALIZED DICT
    if dominant_emotions:
        emotion_counts = Counter(dominant_emotions)
        total = sum(emotion_counts.values())
        emotion_distribution = {
            emotion: round(count / total, 4)
            for emotion, count in emotion_counts.items()
        }
    else:
        emotion_distribution = {}

    avg_hand_movement = float(np.mean(hand_movement_scores))

    return {
        "blink_rate": blink_rate,
        "eye_contact_percent": eye_contact_percent,
        "emotion_distribution": emotion_distribution,
        "avg_hand_movement": avg_hand_movement
    }