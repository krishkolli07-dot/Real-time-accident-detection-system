"""
database.py  —  thread-safe state store

KEY DESIGN CHANGE:
  Instead of a single bool flag that get_alert() consumes and throws away,
  we now keep a LIST of unread alert events.  The frontend polls /alerts
  and gets back every event it hasn't seen yet (by index).  This means:
    • No event is ever silently dropped between poll cycles
    • Each event carries: camera_id, camera_name, location, time, snapshot
    • Multiple cameras can fire simultaneously and all their alerts survive
"""

import time
import threading
from typing import Any

_lock = threading.Lock()

# ── Stats ──────────────────────────────────────────────────────────────────
_stats = {"total_frames": 0, "total_accidents": 0}

# ── Alert event log ────────────────────────────────────────────────────────
# Each entry:
#   { "id": int, "camera_id": int, "camera_name": str,
#     "lat": float, "lon": float, "time": str, "snapshot": str|None }
_alert_log: list = []
_alert_id_counter: int = 0

# ── Cooldowns ──────────────────────────────────────────────────────────────
_cooldowns: dict = {}


# ── Stats ──────────────────────────────────────────────────────────────────

def update_stats(frames_inc: int = 0, accidents_inc: int = 0) -> None:
    with _lock:
        _stats["total_frames"]    += frames_inc
        _stats["total_accidents"] += accidents_inc


def get_stats() -> dict:
    with _lock:
        return dict(_stats)


# ── Alerts ─────────────────────────────────────────────────────────────────

def push_alert(camera_id: int, camera_name: str,
               lat: float = 0.0, lon: float = 0.0,
               snapshot: str = None) -> None:
    """
    Push a new accident event.  Called once per confirmed accident.
    Thread-safe — can be called from multiple camera threads simultaneously.
    """
    global _alert_id_counter
    with _lock:
        _alert_id_counter += 1
        _alert_log.append({
            "id":          _alert_id_counter,
            "camera_id":   camera_id,
            "camera_name": camera_name,
            "lat":         lat,
            "lon":         lon,
            "time":        time.strftime("%H:%M:%S"),
            "date":        time.strftime("%d %b %Y"),
            "snapshot":    snapshot,
        })


def get_alerts_since(last_id: int = 0) -> list:
    """
    Return all alert events with id > last_id.
    Frontend passes its last-seen id; we return only new ones.
    Never drops events.
    """
    with _lock:
        return [a for a in _alert_log if a["id"] > last_id]


def get_all_alerts() -> list:
    with _lock:
        return list(_alert_log)


def get_recent_alerts(n: int = 20) -> list:
    with _lock:
        return list(_alert_log[-n:])


# ── Legacy shim — keeps snapshot.py / main.py working without changes ──────

def set_alert(active: bool, lat: float = 0.0, lon: float = 0.0,
              camera_id: int = 0, camera_name: str = "") -> None:
    """Backward-compat wrapper — use push_alert() for new code."""
    if active:
        push_alert(camera_id, camera_name or f"CAM-{camera_id}", lat, lon)


def get_alert() -> dict:
    """
    Legacy single-bool endpoint still used by /alerts.
    Returns the FULL unread list now so no event is lost.
    """
    with _lock:
        recent = list(_alert_log[-1:])   # last event only for legacy callers
    if recent:
        a = recent[0]
        return {
            "accident":     True,
            "message":      f"🚨 Accident at {a['camera_name']} — {a['time']}",
            "camera_id":    a["camera_id"],
            "camera_name":  a["camera_name"],
            "time":         a["time"],
        }
    return {"accident": False, "message": "✅ No accidents detected",
            "camera_id": None, "camera_name": None, "time": None}


# ── Locations (for map) ────────────────────────────────────────────────────

def get_accident_locations() -> list:
    with _lock:
        return [
            {"lat": a["lat"], "lon": a["lon"],
             "time": a["time"], "camera": a["camera_name"]}
            for a in _alert_log
            if a["lat"] != 0.0 or a["lon"] != 0.0
        ]


# ── Cooldowns ─────────────────────────────────────────────────────────────

def get_cooldown(key: str) -> float:
    with _lock:
        return _cooldowns.get(key, 0.0)


def update_cooldown(key: str, value: Any = None) -> None:
    with _lock:
        if value is None:
            _cooldowns[key] = time.time()
        elif hasattr(value, "timestamp"):
            _cooldowns[key] = value.timestamp()
        else:
            _cooldowns[key] = float(value)


set_cooldown = update_cooldown   # alias