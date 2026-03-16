import cv2
import os
import time

def record_video(frames):

    os.makedirs("backend/accident_videos", exist_ok=True)

    filename = f"backend/accident_videos/accident_{int(time.time())}.mp4"

    height, width, _ = frames[0].shape

    out = cv2.VideoWriter(
        filename,
        cv2.VideoWriter_fourcc(*'mp4v'),
        20,
        (width, height)
    )

    for f in frames:
        out.write(f)

    out.release()