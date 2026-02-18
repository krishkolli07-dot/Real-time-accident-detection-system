import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import cv2
from detector import detect_vehicles

def start_stream():
    cap = cv2.VideoCapture(0)

    if not cap.isOpened():
        print("❌ Camera not accessible")
        return

    print("✅ Camera started. Press 'q' to quit.")

    while True:
        ret, frame = cap.read()
        if not ret:
            print("❌ Failed to grab frame")
            break

        # 🔥 FIX: unpack return values
        results, accident = detect_vehicles(frame)

        for r in results:
            frame = r.plot()

        if accident:
            cv2.putText(
                frame,
                "🚨 ACCIDENT DETECTED",
                (40, 60),
                cv2.FONT_HERSHEY_SIMPLEX,
                1.4,
                (0, 0, 255),
                3
            )

        cv2.imshow("Smart City Traffic AI", frame)

        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

    cap.release()
    cv2.destroyAllWindows()

if __name__ == "__main__":
    start_stream()
