from pathlib import Path

import cv2
import numpy as np
import mediapipe as mp
from mediapipe.tasks.python import BaseOptions
from mediapipe.tasks.python.vision import (
    HandLandmarker,
    HandLandmarkerOptions,
    RunningMode,
)
from pythonosc.udp_client import SimpleUDPClient

MODEL_PATH = str(Path(__file__).parent / "hand_landmarker.task")
INDEX_TIP = 8      # 人差し指の先
LOST_LIMIT = 10     # 何フレーム続けて見失ったらオフにするか（30fpsで約270ms）

GREEN = (0, 255, 0)
RED = (0, 0, 255)      # OpenCV の色は BGR の順
WHITE = (255, 255, 255)


def clamp01(value):
    """手が画面からはみ出すと 0〜1 の外に出るので、切り詰めておく"""
    return min(max(float(value), 0.0), 1.0)


client = SimpleUDPClient("127.0.0.1", 8000)

options = HandLandmarkerOptions(
    base_options=BaseOptions(model_asset_path=MODEL_PATH),
    running_mode=RunningMode.IMAGE,
    num_hands=2,
)
landmarker = HandLandmarker.create_from_options(options)

capture = cv2.VideoCapture(0)
lost = {"left": LOST_LIMIT, "right": LOST_LIMIT}   # 見失っているフレーム数

print("カメラを起動しました。q キーで終了します。")

while capture.isOpened():
    ok, frame = capture.read()
    if not ok:
        break

    frame = cv2.flip(frame, 1)  # 鏡像にすると操作感が自然になる
    rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb)

    result = landmarker.detect(image)

    # カメラ映像は表示せず、黒い画面にランドマークだけを描く
    h, w = frame.shape[:2]
    canvas = np.zeros((h, w, 3), dtype=np.uint8)

    detected = {"left": False, "right": False}

    for hand, handed in zip(result.hand_landmarks, result.handedness):
        label = handed[0].category_name.lower()   # "left" または "right"
        detected[label] = True

        # 座標は 0〜1 に正規化されているので、そのまま送れる
        index_tip = hand[INDEX_TIP]
        client.send_message(f"/{label}/x", clamp01(index_tip.x))
        client.send_message(f"/{label}/y", clamp01(index_tip.y))

        # 0〜1 の座標を画面のピクセル位置に直す
        points = []
        for landmark in hand:
            points.append((int(landmark.x * w), int(landmark.y * h)))


        # 各点。人差し指の先だけ赤くする
        for i, point in enumerate(points):
            color = RED if i == INDEX_TIP else GREEN
            radius = 20 if i == INDEX_TIP else 15
            cv2.circle(canvas, point, radius, color, -1)

    # 手が検出されているかどうかを毎フレーム送る。
    # 一瞬の検出漏れで音が切れないよう、LOST_LIMIT フレームぶんの猶予をもたせる。
    for label in ("left", "right"):
        if detected[label]:
            lost[label] = 0
        else:
            lost[label] += 1
        client.send_message(f"/{label}/on", 1 if lost[label] < LOST_LIMIT else 0)

    cv2.imshow("hand", canvas)
    if cv2.waitKey(1) & 0xFF == ord("q"):
        break

capture.release()
cv2.destroyAllWindows()
landmarker.close()