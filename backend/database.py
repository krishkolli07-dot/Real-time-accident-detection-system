from datetime import datetime

latest_alert = {
    "accident": False,
    "timestamp": None
}

def set_alert(status: bool):
    latest_alert["accident"] = status
    latest_alert["timestamp"] = datetime.now().isoformat()

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
