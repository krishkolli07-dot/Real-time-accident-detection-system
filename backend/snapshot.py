import cv2
import os
from datetime import datetime

SAVE_DIR = "backend/accidents"
os.makedirs(SAVE_DIR, exist_ok=True)

last_saved_time = None
COOLDOWN_SECONDS = 5   # prevent spam

def save_accident_frame(frame):
    global last_saved_time

    now = datetime.now()

    if last_saved_time:
        diff = (now - last_saved_time).total_seconds()
        if diff < COOLDOWN_SECONDS:
            return None

    filename = now.strftime("accident_%Y%m%d_%H%M%S.jpg")
    path = os.path.join(SAVE_DIR, filename)

    cv2.imwrite(path, frame)
    last_saved_time = now

    return filename
