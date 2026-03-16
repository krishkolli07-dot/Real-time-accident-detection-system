import cv2
import os
from datetime import datetime
import time
from backend.database import get_cooldown, update_cooldown

SAVE_DIR = "backend/accidents"
os.makedirs(SAVE_DIR, exist_ok=True)

def save_accident_frame(frame):
    now = datetime.now()
    last_snapshot = get_cooldown("last_snapshot_time")
    if last_snapshot:
        diff = (now - last_snapshot).total_seconds()
        if diff < 5:
            return None

    filename = now.strftime("accident_%Y%m%d_%H%M%S.jpg")
    path = os.path.join(SAVE_DIR, filename)

    cv2.imwrite(path, frame)
    update_cooldown("last_snapshot_time", now)

    return filename
