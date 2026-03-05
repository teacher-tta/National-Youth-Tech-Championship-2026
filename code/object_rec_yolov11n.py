import cv2
from ultralytics import YOLO

model = YOLO("yolo11n.pt")

cap = cv2.VideoCapture(0)

## UGOT version
# import numpy as np
# from ugot import ugot
# got = ugot.UGOT()
# got.initialize("192.168.1.189") # replace this with your UGOT IP address
# got.open_camera()

while True:
    # webcam
    ret, frame = cap.read()
    if not ret:
        break
    # ------------------------------
    ## UGOT version
    # frame = got.read_camera_data()
    # if frame is None:
    #     continue
    # nparr = np.frombuffer(frame, np.uint8)
    # frame = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
    # ------------------------------

    results = model(frame, conf=0.4, imgsz=640, device="cpu")

    for r in results:
        for box in r.boxes:
            x1, y1, x2, y2 = map(int, box.xyxy[0])
            cls = int(box.cls[0])
            conf = float(box.conf[0])

            cv2.rectangle(frame, (x1, y1), (x2, y2), (0,255,0), 2)
            cv2.putText(frame, f"{model.names[cls]} {conf:.2f}",
                        (x1, y1 - 8), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0,255,0), 2)

    cv2.imshow("YOLOv11", frame)
    if cv2.waitKey(1) & 0xFF == 27:
        break

cap.release()
cv2.destroyAllWindows()
