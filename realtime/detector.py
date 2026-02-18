import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from ultralytics import YOLO
from utils.tracker import VehicleTracker
import cv2

model = YOLO("yolov8n.pt")
tracker = VehicleTracker()

def box_center(box):
    x1, y1, x2, y2 = box
    return ((x1 + x2) // 2, (y1 + y2) // 2)

def detect_vehicles(frame):
    results = model(frame, conf=0.4, classes=[2, 3, 5, 7])
    accident_detected = False
    vehicle_id = 0

    for r in results:
        if r.boxes is None:
            continue

        for box in r.boxes.xyxy.cpu().numpy():
            x1, y1, x2, y2 = map(int, box)
            center = box_center(box)

            if tracker.update(vehicle_id, center):
                accident_detected = True
                cv2.putText(
                    frame,
                    "ACCIDENT!",
                    (x1, y1 - 10),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.8,
                    (0, 0, 255),
                    2
                )

            # Draw bounding box
            cv2.rectangle(
                frame,
                (x1, y1),
                (x2, y2),
                (0, 255, 0),
                2
            )

            vehicle_id += 1

    return frame, accident_detected
