from datetime import datetime
import time

latest_alert = {
    "accident": False,
    "timestamp": None
}

stats = {
    "total_frames": 0,
    "total_accidents": 0
}

cooldowns = {
    "last_alert_time": 0,
    "last_snapshot_time": None
}

def set_alert(status: bool):
    latest_alert["accident"] = status
    latest_alert["timestamp"] = datetime.now().isoformat()
    cooldowns["last_alert_time"] = time.time()

def get_stats():
    return stats

def update_stats(frames_inc=1, accidents_inc=0):
    stats["total_frames"] += frames_inc
    stats["total_accidents"] += accidents_inc

def get_cooldown(key):
    return cooldowns[key]

def update_cooldown(key, value):
    cooldowns[key] = value

def get_alert():
    return latest_alert

def get_accident_locations():
    # Dummy data for now (replace later with real GPS)
    return {
        "accidents": [
            {
                "lat": 17.385044,
                "lng": 78.486671,
                "severity": "HIGH",
                "time": "10:42 AM"
            },
            {
                "lat": 17.392,
                "lng": 78.480,
                "severity": "LOW",
                "time": "11:05 AM"
            }
        ]
    }
