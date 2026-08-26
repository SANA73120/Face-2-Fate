#!/usr/bin/env bash
# download_models.sh
# Downloads the MediaPipe model files required by Face 2 Fate.
# Run this from the project root (where app.py lives).
#
# Usage:
#   chmod +x download_models.sh
#   ./download_models.sh

set -e

echo "Downloading face_landmarker.task ..."
curl -L -o face_landmarker.task \
  https://storage.googleapis.com/mediapipe-models/face_landmarker/face_landmarker/float16/latest/face_landmarker.task

echo "Downloading hand_landmarker.task ..."
curl -L -o hand_landmarker.task \
  https://storage.googleapis.com/mediapipe-models/hand_landmarker/hand_landmarker/float16/latest/hand_landmarker.task

echo ""
echo "Done. face_landmarker.task and hand_landmarker.task are now in the project root."
echo ""
echo "NOTE: enet_b0_8_best_afew.onnx (HSEmotion model) is NOT downloaded by this script."
echo "Get it manually from https://github.com/HSE-asavchenko/face-emotion-recognition"
echo "(see models/affectnet_emotions/onnx in that repo) and place it at: models/enet_b0_8_best_afew.onnx"
