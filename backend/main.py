from fastapi import FastAPI
from fastapi.responses import JSONResponse, FileResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
import cv2
import os
import time
import requests
import numpy as np
import urllib3


from backend.database import set_alert
from backend.database import get_accident_locations
from realtime.detector import detect_vehicles
from backend.snapshot import save_accident_frame
from backend.report import generate_report

app = FastAPI()
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# ---------------- GLOBAL STATE ----------------
total_frames = 0
total_accidents = 0
alert_expiry_time = 0
CAMERAS = {
    1: {
        "name": "Trimarc KY446",
        "url": "https://www.trimarc.org/images/milestone/CCTV_03_KY446_0002.jpg"
    },
    2: {
        "name": "Local Webcam",
        "url": "https://www.trimarc.org/images/milestone/CCTV_03_ScottsvilleRd_and_LoversLn.jpg"
    }B
}

# ---------------- CONFIG ----------------
video_path = 0

# ---------------- FRONTEND ----------------
app.mount("/static", StaticFiles(directory="frontend"), name="static")
app.mount("/accidents", StaticFiles(directory="backend/accidents"), name="accidents")


@app.get("/")
def serve_frontend():
    return FileResponse("frontend/index.html")


# ================= ANALYSIS =================
@app.get("/analyze")
def analyze_video():
    global total_frames, total_accidents

    risk = "HIGH" if total_accidents > 3 else "LOW"

    return {
        "frames_processed": total_frames,
        "accidents_detected": total_accidents,
        "risk_level": risk
    }


# ================= VIDEO STREAM =================
def video_generator(cam_id):
    camera = CAMERAS.get(cam_id)

    if not camera:
        return

    while True:
        try:
            # Snapshot camera (URL)
            if isinstance(camera["url"], str):
                headers = {
                    "User-Agent": "Mozilla/5.0"
                }

                response = requests.get(
                    camera["url"],
                    headers=headers,
                    timeout=5,
                    verify=False

                )

                if response.status_code != 200:
                    time.sleep(3)
                    continue

                img_array = np.frombuffer(response.content, np.uint8)
                frame = cv2.imdecode(img_array, cv2.IMREAD_COLOR)

                if frame is None:
                    time.sleep(3)
                    continue

                time.sleep(3)

            # Local webcam
            else:
                cap = cv2.VideoCapture(camera["url"])
                ret, frame = cap.read()

                if not ret:
                    continue

            # Run detection
            frame, accident = detect_vehicles(frame)

            if accident:
                set_alert(True)
                save_accident_frame(frame)

            _, buffer = cv2.imencode(".jpg", frame)

            yield (
                b"--frame\r\n"
                b"Content-Type: image/jpeg\r\n\r\n" +
                buffer.tobytes() +
                b"\r\n"
            )

        except Exception as e:
            print("Camera error:", e)
            time.sleep(5)



@app.get("/video/{cam_id}")
def video_feed(cam_id: int):
    return StreamingResponse(
        video_generator(cam_id),
        media_type="multipart/x-mixed-replace; boundary=frame"
    )



# ================= ALERTS =================
@app.get("/alerts")
def accident_alert():
    global alert_expiry_time

    if time.time() < alert_expiry_time:
        return {"message": "🚨 Accident Detected!"}
    else:
        return {"message": "No active accidents"}


# ================= ACCIDENT IMAGES =================
@app.get("/accident-images")
def get_accident_images():
    folder = "backend/accidents"

    if not os.path.exists(folder):
        return {"images": []}

    images = sorted(os.listdir(folder), reverse=True)

    return {"images": images[:5]}


# ================= DOWNLOAD REPORT =================
@app.get("/download-report")
def download_report():
    cap = cv2.VideoCapture(video_path)

    accidents = 0
    frames = 0

    while True:
        ret, frame = cap.read()
        if not ret:
            break

        _, accident = detect_vehicles(frame)
        frames += 1

        if accident:
            accidents += 1

    cap.release()

    risk = "HIGH" if accidents > 3 else "LOW"

    pdf_path = generate_report(frames, accidents, risk)

    return FileResponse(
        pdf_path,
        media_type="application/pdf",
        filename="traffic_accident_report.pdf"
    )


# ================= MAP =================
@app.get("/map-data")
def map_data():
    return get_accident_locations()
