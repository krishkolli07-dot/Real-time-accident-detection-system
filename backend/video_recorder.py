import cv2
import os
from collections import deque
import time

buffer = deque(maxlen=150)  # ~5 seconds buffer (30fps)

recording = False
out = None
record_start = None

def record_video(frame, accident=False):

    global recording, out, record_start

    buffer.append(frame)

    # Start recording
    if accident and not recording:

        filename = f"backend/accidents/accident_{int(time.time())}.mp4"

        h, w, _ = frame.shape

        out = cv2.VideoWriter(
            filename,
            cv2.VideoWriter_fourcc(*'mp4v'),
            20,
            (w, h)
        )

        # write past frames (buffer)
        for f in buffer:
            out.write(f)

        recording = True
        record_start = time.time()

    # Continue recording for 10 seconds
    if recording:

        out.write(frame)

        if time.time() - record_start > 10:
            recording = False
            out.release()