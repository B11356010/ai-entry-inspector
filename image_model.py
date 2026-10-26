
from ultralytics import YOLO
from PIL import Image

_model = None


def get_model():
    global _model

    if _model is None:
        _model = YOLO("yolo26n.pt")

    return _model


def detect_objects(image):
    """偵測圖片中的多個物品，回傳辨識清單和標記後的圖片。"""

    model = get_model()

    results = model.predict(
        source=image,
        conf=0.25,
        verbose=False
    )

    # 即使沒有偵測結果，也回傳兩個值
    if not results:
        return [], image

    result = results[0]
    detections = []

    for box in result.boxes:
        class_id = int(box.cls[0].item())
        label = result.names[class_id]
        score = float(box.conf[0].item())

        detections.append({
            "label": label,
            "score": score
        })

    # YOLO 的繪圖結果是 BGR，需要轉成 RGB
    annotated_array = result.plot()
    annotated_image = Image.fromarray(
        annotated_array[:, :, ::-1].copy()
    )

    # 一定回傳兩個值
    return detections, annotated_image
