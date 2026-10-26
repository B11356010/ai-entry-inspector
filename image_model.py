
from ultralytics import YOLO
from PIL import Image

# 延遲載入模型，避免每次辨識都重新載入
_model = None


def get_model():
    global _model

    if _model is None:
        _model = YOLO("yolo26n.pt")

    return _model


def detect_objects(image):
    """辨識照片中的多個物品，並回傳標示方框的圖片。"""

    model = get_model()

    # 執行物件偵測
    results = model.predict(
        source=image,
        conf=0.25,
        verbose=False
    )

    result = results[0]
    detections = []

    # 整理每個偵測到的物品
    for box in result.boxes:
        class_id = int(box.cls[0].item())
        label = result.names[class_id]
        score = float(box.conf[0].item())

        detections.append({
            "label": label,
            "score": score
        })

    # 在圖片上畫出辨識方框
