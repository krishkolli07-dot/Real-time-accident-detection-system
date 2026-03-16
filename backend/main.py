from fastapi import FastAPI
from fastapi.responses import FileResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles

import cv2
import os
import time
import requests
import numpy as np
import urllib3

from backend.database import set_alert, get_accident_locations, get_stats, update_stats, get_cooldown
from backend.emergency_services import nearby_services
from realtime.detector import detect_vehicles
from backend.snapshot import save_accident_frame
from backend.report import generate_report
from backend.emergency_services import nearby_services  

app = FastAPI()



# ---------------- GLOBAL STATE ----------------
# Moved to database.py for thread-safety


# ---------------- CAMERA CONFIG ----------------
CAMERAS = {

    1: {
        "name": "CCTV Camera",
        "type": "snapshot",
        "url": "https://www.trimarc.org/images/milestone/CCTV_03_KY446_0002.jpg"
    },

    2: {
        "name": "Webcam",
        "type": "webcam",
        "url": 0
    },

    3: {
        "name": "Recorded Video",
        "type": "video",
        "path": "videos/traffic.mp4"
    }

}


# ---------------- STATIC FILES ----------------
app.mount("/static", StaticFiles(directory="frontend"), name="static")
app.mount("/accidents", StaticFiles(directory="backend/accidents"), name="accidents")


# ---------------- FRONTEND ----------------
@app.get("/")
def home():
    return FileResponse("frontend/index.html")


# ---------------- ANALYSIS ----------------
@app.get("/analyze")
def analyze():
    stats = get_stats()
    risk = "HIGH" if stats["total_accidents"] > 3 else "LOW"

    return {
        "frames_processed": stats["total_frames"],
        "accidents_detected": stats["total_accidents"],
        "risk_level": risk
    }


# ---------------- VIDEO STREAM ----------------
def video_stream(cam_id: int):

    global total_frames, total_accidents, last_alert_time

    camera = CAMERAS.get(cam_id)

    cap = None

    if camera["type"] == "webcam":
        cap = cv2.VideoCapture(camera["url"])

    if camera["type"] == "video":
        cap = cv2.VideoCapture(camera["path"])

    while True:

        try:

            # -------- SNAPSHOT CAMERA --------
            if camera["type"] == "snapshot":

                response = requests.get(
                    camera["url"],
                    headers={"User-Agent": "Mozilla/5.0"},
                    timeout=10,
                    verify=False
                )

                img_array = np.frombuffer(response.content, np.uint8)
                frame = cv2.imdecode(img_array, cv2.IMREAD_COLOR)

                time.sleep(2)

            # -------- WEBCAM / VIDEO --------
            else:

                ret, frame = cap.read()

                if not ret:

                    # restart video
                    cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
                    continue

            if frame is None:
                continue

            frame, accident = detect_vehicles(frame)

            update_stats(1)

            if accident:

                update_stats(accidents_inc=1)

                if time.time() - get_cooldown("last_alert_time") > 15:

                    set_alert(True)
                    save_accident_frame(frame)

            _, buffer = cv2.imencode(".jpg", frame)

            yield (
                b'--frame\r\n'
                b'Content-Type: image/jpeg\r\n\r\n' +
                buffer.tobytes() +
                b'\r\n'
            )

        except Exception as e:

            print("Camera error:", e)
            time.sleep(3)


@app.get("/video/{cam_id}")
def video_feed(cam_id: int):

    return StreamingResponse(
        video_stream(cam_id),
        media_type="multipart/x-mixed-replace; boundary=frame"
    )


# ---------------- ALERTS ----------------
@app.get("/alerts")
def alerts():

    if time.time() - last_alert_time < 10:
        return {"message": "🚨 Accident Detected!"}

    return {"message": "No active accidents"}


# ---------------- ACCIDENT IMAGES ----------------
@app.get("/accident-images")
def accident_images():

    folder = "backend/accidents"

    if not os.path.exists(folder):
        return {"images": []}

    images = sorted(os.listdir(folder), reverse=True)

    return {"images": images[:5]}


# ---------------- REPORT ----------------
@app.get("/download-report")
def report():
    stats = get_stats()
    risk = "HIGH" if stats["total_accidents"] > 3 else "LOW"

    pdf = generate_report(stats["total_frames"], stats["total_accidents"], risk)

    return FileResponse(
        pdf,
        media_type="application/pdf",
        filename="accident_report.pdf"
    )


# ---------------- MAP DATA ----------------
@app.get("/map-data")
def map_data():

    data = get_accident_locations()

    return {"accidents": data}

@app.get("/services")
def services():
    return {
        "ambulances":[
            {"lat":17.386,"lng":78.487,"name":"City Ambulance"}
        ],
        "hospitals":[
            {"lat":17.384,"lng":78.480,"name":"Apollo Hospital"}
        ],
        "police":[
            {"lat":17.381,"lng":78.488,"name":"Traffic Police Station"}
        ]
    }