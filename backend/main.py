"""
backend/main.py

Run from project ROOT:
    uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload

FIXES vs original:
  • dispatch_services imported and actually called on each accident
    (was completely orphaned — defined in emergency_dispatch.py but never
    used anywhere in the backend)
  • push_alert() now receives the full snapshot filename so the accident
    report PDF can correctly embed the image
  • snap_path construction unified — was being built then ignored by push_alert
"""

from fastapi import FastAPI, Query, Body
from fastapi.responses import FileResponse, StreamingResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pathlib import Path

import cv2, os, queue, threading, time, requests, numpy as np
import urllib3
urllib3.disable_warnings()

import sys
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

# ── Relative imports for backend/ siblings ────────────────────────────────────
from .database import (
    push_alert, get_alerts_since, get_recent_alerts, get_all_alerts,
    get_accident_locations, get_stats, update_stats,
    get_cooldown, update_cooldown, get_alert,
)
from .emergency_services import nearby_services
from .emergency_dispatch import dispatch_services   # FIX: was never imported
from .snapshot import save_accident_frame
from .report import generate_report, generate_accident_report
from .notifier import send_accident_alert

# ── Absolute import for realtime/ ────────────────────────────────────────────
from realtime.detector import detect_vehicles

# ── App setup ─────────────────────────────────────────────────────────────────
app      = FastAPI()
BASE_DIR = ROOT

os.makedirs("backend/accidents", exist_ok=True)
os.makedirs("backend/reports",   exist_ok=True)

app.mount("/static",    StaticFiles(directory=str(BASE_DIR / "frontend" / "static")), name="static")
app.mount("/accidents", StaticFiles(directory="backend/accidents"),                    name="accidents")

# ── Camera config ─────────────────────────────────────────────────────────────
CAMERAS = {
    1: {
        "name": "CCTV Camera", "location": "Highway Junction",
        "type": "snapshot",
        "url":  "https://www.trimarc.org/images/milestone/CCTV_03_KY446_0002.jpg",
        "lat": 38.2527, "lon": -85.7585,
    },
    2: {
        "name": "Recorded Video 2", "location": "Main Road",
        "type": "video", "path": "videos/traffic.mp4",
        "lat": 16.240, "lon": 80.550,
    },
    3: {
        "name": "Recorded Video 3", "location": "City Center",
        "type": "video", "path": "videos/traffic2.mp4",
        "lat": 16.241, "lon": 80.552,
    },
}

ALERT_COOLDOWN = 120   # seconds between alerts per camera

_lock         = threading.Lock()
_frame_queues = {cid: queue.Queue(maxsize=2) for cid in CAMERAS}
_cam_enabled  = {cid: True for cid in CAMERAS}
_cam_source   = {}
_worker_stop  = {cid: threading.Event() for cid in CAMERAS}


def _push_frame(cam_id, buf):
    q = _frame_queues[cam_id]
    try:
        q.put_nowait(buf)
    except queue.Full:
        try:    q.get_nowait()
        except: pass
        try:    q.put_nowait(buf)
        except: pass


def _camera_worker(cam_id):
    camera = CAMERAS[cam_id]
    cap    = None
    print(f"[CAM-{cam_id}] started — {camera['name']}")

    while not _worker_stop[cam_id].is_set():
        with _lock:
            enabled = _cam_enabled[cam_id]
        if not enabled:
            time.sleep(0.5); continue

        try:
            if camera["type"] == "snapshot":
                r     = requests.get(camera["url"],
                                     headers={"User-Agent": "Mozilla/5.0"},
                                     timeout=10, verify=False)
                img   = np.frombuffer(r.content, np.uint8)
                frame = cv2.imdecode(img, cv2.IMREAD_COLOR)
                if frame is None: time.sleep(2); continue
                time.sleep(2)
            else:
                with _lock:
                    override = _cam_source.get(cam_id)
                src = (override if override is not None
                       else camera.get("url") if camera["type"] == "webcam"
                       else camera.get("path", ""))

                if cap is None or not cap.isOpened():
                    cap = cv2.VideoCapture(src)
                    if not cap.isOpened():
                        print(f"[CAM-{cam_id}] cannot open: {src}")
                        time.sleep(3); continue
                    print(f"[CAM-{cam_id}] opened: {src}")

                with _lock:
                    new_src = _cam_source.get(cam_id)
                if new_src is not None and new_src != src:
                    cap.release(); cap = None; continue

                ret, frame = cap.read()
                if not ret:
                    if camera["type"] == "video":
                        cap.set(cv2.CAP_PROP_POS_FRAMES, 0); continue
                    cap.release(); cap = None; time.sleep(2); continue

            frame, accident = detect_vehicles(frame, cam_id)
            update_stats(frames_inc=1)

            if accident:
                key = f"alert_cooldown_{cam_id}"
                if time.time() - get_cooldown(key) > ALERT_COOLDOWN:
                    update_stats(accidents_inc=1)
                    update_cooldown(key)

                    snap = save_accident_frame(frame, cam_id)

                    # FIX: build full path for notifier, but store only the
                    # filename in push_alert so /accidents/<file> URLs work.
                    snap_full_path = (
                        os.path.join("backend/accidents", snap) if snap else None
                    )

                    push_alert(
                        camera_id=cam_id,
                        camera_name=camera["name"],
                        lat=camera["lat"],
                        lon=camera["lon"],
                        snapshot=snap,           # filename only for URL construction
                    )

                    # FIX: dispatch_services was never called — it was only
                    # defined in emergency_dispatch.py and printed to console.
                    # Now it fires on every confirmed accident.
                    try:
                        dispatch_services(camera["lat"], camera["lon"])
                    except Exception as e:
                        print(f"[CAM-{cam_id}] dispatch error: {e}")

                    send_accident_alert(
                        camera_id=cam_id,
                        camera_name=camera["name"],
                        location=camera["location"],
                        lat=camera["lat"],
                        lon=camera["lon"],
                        snapshot_path=snap_full_path,   # full path for email attachment
                    )

                    print(f"[CAM-{cam_id}] ACCIDENT at {camera['location']}")

            _, buf = cv2.imencode(".jpg", frame, [cv2.IMWRITE_JPEG_QUALITY, 78])
            _push_frame(cam_id, buf.tobytes())

        except Exception as e:
            print(f"[CAM-{cam_id}] error: {e}")
            if cap:
                try: cap.release()
                except: pass
                cap = None
            time.sleep(3)


for _cid in CAMERAS:
    threading.Thread(target=_camera_worker, args=(_cid,), daemon=True).start()
    print(f"[startup] Camera {_cid} launched")


def _stream(cam_id):
    while True:
        with _lock:
            enabled = _cam_enabled[cam_id]
        if not enabled:
            ph = np.zeros((240, 320, 3), np.uint8)
            cv2.putText(ph, "CAMERA OFF", (55, 125),
                        cv2.FONT_HERSHEY_SIMPLEX, 1, (80, 80, 80), 2)
            _, buf = cv2.imencode(".jpg", ph)
            yield (b"--frame\r\nContent-Type: image/jpeg\r\n\r\n"
                   + buf.tobytes() + b"\r\n")
            time.sleep(1); continue
        try:
            data = _frame_queues[cam_id].get(timeout=3)
            yield (b"--frame\r\nContent-Type: image/jpeg\r\n\r\n" + data + b"\r\n")
        except queue.Empty:
            yield b"--frame\r\nContent-Type: text/plain\r\n\r\nwaiting\r\n"


# ══════════════════════════════════════════════════════════════════════════════
# ENDPOINTS
# ══════════════════════════════════════════════════════════════════════════════

@app.get("/")
def home():
    return FileResponse(str(BASE_DIR / "frontend" / "index.html"))


@app.get("/analyze")
def analyze():
    s = get_stats(); acc = s["total_accidents"]
    return {
        "frames_processed":   s["total_frames"],
        "accidents_detected": acc,
        "risk_level": "HIGH" if acc > 3 else "MEDIUM" if acc > 0 else "LOW",
    }


@app.get("/video/{cam_id}")
def video_feed(cam_id: int):
    return StreamingResponse(_stream(cam_id),
        media_type="multipart/x-mixed-replace; boundary=frame")


@app.get("/camera/status")
def camera_status():
    with _lock:
        return {str(c): {"enabled": _cam_enabled[c], "name": CAMERAS[c]["name"],
                          "location": CAMERAS[c]["location"], "type": CAMERAS[c]["type"]}
                for c in CAMERAS}


@app.post("/camera/{cam_id}/toggle")
def toggle_camera(cam_id: int):
    with _lock:
        if cam_id not in CAMERAS:
            return JSONResponse({"error": "unknown cam"}, status_code=404)
        _cam_enabled[cam_id] = not _cam_enabled[cam_id]
        state = _cam_enabled[cam_id]
    return {"cam_id": cam_id, "enabled": state}


@app.post("/camera/{cam_id}/source")
def set_source(cam_id: int, body: dict = Body(...)):
    path = body.get("path", "").strip()
    if cam_id not in CAMERAS:
        return JSONResponse({"error": "unknown cam"}, status_code=404)
    new_src = int(path) if path.isdigit() else path
    with _lock:
        _cam_source[cam_id] = new_src
    return {"cam_id": cam_id, "source": str(new_src)}


@app.get("/alerts/stream")
def alerts_stream(since: int = Query(default=0)):
    new = get_alerts_since(since)
    return JSONResponse({"alerts": [
        {**a, "location": CAMERAS.get(a["camera_id"], {}).get("location", "Unknown")}
        for a in new
    ]})


@app.get("/alerts/recent")
def alerts_recent():
    return JSONResponse({"alerts": [
        {**a, "location": CAMERAS.get(a["camera_id"], {}).get("location", "Unknown")}
        for a in get_recent_alerts(20)
    ]})


@app.get("/alerts")
def alerts_legacy():
    return get_alert()


@app.get("/accident-images")
def accident_images():
    folder = "backend/accidents"
    if not os.path.exists(folder): return {"images": []}
    imgs = sorted([f for f in os.listdir(folder) if f.endswith(".jpg")], reverse=True)
    return {"images": imgs[:10]}


@app.get("/download-report")
def full_report():
    s    = get_stats()
    risk = "HIGH" if s["total_accidents"] > 3 else "LOW"
    pdf  = generate_report(s["total_frames"], s["total_accidents"], risk)
    return FileResponse(pdf, media_type="application/pdf", filename="summary_report.pdf")


@app.post("/download-accident-report")
def accident_report_download(body: dict = Body(...)):
    ids        = body.get("ids", [])
    all_alerts = get_all_alerts()
    # FIX: generate_accident_report now correctly takes (ids, all_alerts)
    # Old report.py had signature (frames, accidents, risk) — completely wrong
    pdf        = generate_accident_report(ids, all_alerts)
    ids_str    = "_".join(str(i) for i in ids[:4]) if ids else "all"
    return FileResponse(pdf, media_type="application/pdf",
                        filename=f"accident_report_{ids_str}.pdf")


@app.get("/map-data")
def map_data():
    return {"accidents": get_accident_locations()}


@app.get("/services")
def services():
    cam  = CAMERAS.get(2, CAMERAS[1])
    data = nearby_services(cam["lat"], cam["lon"])
    hospitals, ambulances, police = [], [], []
    for e in data.get("elements", []):
        if not (e.get("lat") and e.get("lon")): continue
        tags = e.get("tags", {})
        name = tags.get("name", tags.get("operator", "Service"))
        am   = tags.get("amenity", "").lower()
        em   = tags.get("emergency", "").lower()
        svc  = {"lat": float(e["lat"]), "lng": float(e["lon"]), "name": name}
        if "hospital" in am or "clinic" in am: hospitals.append(svc)
        elif "ambulance" in am or "ambulance" in em: ambulances.append(svc)
        elif "police" in am: police.append(svc)
    return {"hospitals": hospitals, "ambulances": ambulances, "police": police}


@app.get("/alert-page")
def alert_page(lat: float = Query(16.24), lon: float = Query(80.55),
               cam: str = Query(""), loc: str = Query(""), time: str = Query("")):
    return FileResponse(str(BASE_DIR / "frontend" / "neighbourhood_alert.html"))