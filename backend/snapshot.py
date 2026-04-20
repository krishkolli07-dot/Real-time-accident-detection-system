"""
snapshot.py

FIXES vs original:
  • Import changed from `from backend.database import ...` to a try/except
    that first attempts the relative import (for package usage) then falls
    back to the absolute import (for standalone usage).  The old hard-coded
    `from backend.database` import crashed whenever the module was loaded as
    part of the `backend` package (which is always, in production).
"""

import cv2
import os
from datetime import datetime

try:
    from .database import get_cooldown, update_cooldown          # package use
except ImportError:
    from backend.database import get_cooldown, update_cooldown   # fallback

SAVE_DIR          = "backend/accidents"
SNAPSHOT_COOLDOWN = 5   # seconds between snapshots per camera

os.makedirs(SAVE_DIR, exist_ok=True)


def save_accident_frame(frame, cam_id: int = 0) -> str | None:
    """
    Save a JPEG snapshot of the accident frame.

    Returns the filename (not full path) on success, or None if the
    per-camera cooldown has not elapsed yet.
    """
    now       = datetime.now().timestamp()
    key       = f"snap_cooldown_{cam_id}"
    last_snap = get_cooldown(key)

    if (now - last_snap) < SNAPSHOT_COOLDOWN:
        return None

    ts       = datetime.fromtimestamp(now).strftime("%Y%m%d_%H%M%S")
    filename = f"cam{cam_id}_accident_{ts}.jpg"
    path     = os.path.join(SAVE_DIR, filename)
    cv2.imwrite(path, frame)
    update_cooldown(key, now)
    print(f"[snapshot] CAM-{cam_id} saved: {path}")
    return filename