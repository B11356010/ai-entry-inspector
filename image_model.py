"""
image_model.py — 行李物品辨識模組
負責人：歐陽品臻

對外介面（不可任意更改，需變更請先通知所有組員）：
    detections, annotated_image = detect_objects(image)

注意事項：
- 本模組只做「一般物品偵測」，結果不代表任何違禁品或法規判定。
  是否需要查核，請交由 regulation_checker.py 依官方規定判斷。
- score 是模型的信心分數，不是實際準確率。
- 任何情況都回傳 (list, PIL.Image)，不回傳 None，避免主程式解包失敗。
"""

import logging

from PIL import Image

logger = logging.getLogger(__name__)

# ===== 模型設定（沿用組長框架的設定）=====
MODEL_NAME = "yolo26n.pt"
CONF_THRESHOLD = 0.25
IMAGE_SIZE = 1024
IOU_THRESHOLD = 0.45

_model = None


def get_model():
    """載入 YOLO 模型（只載入一次）；失敗時回傳 None，由呼叫端處理。"""
    global _model

    if _model is None:
        try:
            from ultralytics import YOLO
            _model = YOLO(MODEL_NAME)
        except Exception as e:
            logger.error("物品辨識模型載入失敗：%s", e)
            _model = None

    return _model


def _placeholder_image():
    """輸入無效時使用的空白圖片，確保 annotated_image 一定是 PIL Image。"""
    return Image.new("RGB", (1, 1), (255, 255, 255))


def _clamp_box(xyxy, width, height):
    """將座標轉成整數 [x1, y1, x2, y2]，並限制在圖片範圍內。"""
    x1, y1, x2, y2 = [float(v) for v in xyxy]
    x1 = int(round(max(0, min(x1, width))))
    y1 = int(round(max(0, min(y1, height))))
    x2 = int(round(max(0, min(x2, width))))
    y2 = int(round(max(0, min(y2, height))))
    return [x1, y1, x2, y2]


def detect_objects(image):
    """
    偵測圖片中的多個物品，回傳辨識清單和標記後的圖片。

    參數：
        image：PIL Image 圖片物件。

    回傳：
        (detections, annotated_image)
        detections：list，每個元素為
            {"label": str, "score": float (0~1), "box": [x1, y1, x2, y2]}
            座標以原始圖片左上角為起點。沒有偵測到或發生錯誤時為 []。
        annotated_image：PIL Image，已畫上物品框的圖片。
            發生錯誤時回傳未標註的原圖（輸入無效時回傳空白圖片）。
    """
    # 1. 檢查輸入
    if not isinstance(image, Image.Image):
        logger.error("detect_objects 輸入不是 PIL Image：%r", type(image))
        return [], _placeholder_image()

    try:
        # 轉成 RGB，避免 RGBA / P / L 模式造成模型錯誤
        rgb_image = image.convert("RGB") if image.mode != "RGB" else image.copy()
    except Exception as e:
        logger.error("圖片轉換失敗：%s", e)
        return [], _placeholder_image()

    # 2. 載入模型
    model = get_model()
    if model is None:
        return [], rgb_image

    # 3. 推論
    try:
        results = model.predict(
            source=rgb_image,
            conf=CONF_THRESHOLD,
            imgsz=IMAGE_SIZE,
            iou=IOU_THRESHOLD,
            verbose=False
        )
    except Exception as e:
        logger.error("物品辨識失敗：%s", e)
        return [], rgb_image

    # 即使沒有偵測結果，也回傳兩個值
    if not results:
        return [], rgb_image

    result = results[0]

    # 4. 整理偵測結果
    detections = []
    try:
        width, height = rgb_image.size
        for box in result.boxes:
            class_id = int(box.cls[0].item())
            label = str(result.names[class_id])
            score = float(box.conf[0].item())
            xyxy = _clamp_box(box.xyxy[0].tolist(), width, height)

            if xyxy[2] <= xyxy[0] or xyxy[3] <= xyxy[1]:
                continue  # 無效框

            detections.append({
                "label": label,
                "score": round(score, 4),
                "box": xyxy
            })
        detections.sort(key=lambda d: d["score"], reverse=True)
    except Exception as e:
        logger.error("偵測結果整理失敗：%s", e)
        return [], rgb_image

    # 5. 畫框（畫框失敗不影響偵測結果）
    try:
        # YOLO 的繪圖結果是 BGR，需要轉成 RGB
        annotated_array = result.plot()
        annotated_image = Image.fromarray(
            annotated_array[:, :, ::-1].copy()
        )
    except Exception as e:
        logger.error("標註圖片繪製失敗：%s", e)
        annotated_image = rgb_image

    # 一定回傳兩個值
    return detections, annotated_image


if __name__ == "__main__":
    # 本機快速檢查：python image_model.py 照片路徑
    import sys

    logging.basicConfig(level=logging.INFO)
    if len(sys.argv) < 2:
        print("用法：python image_model.py <圖片路徑>")
        sys.exit(0)

    img = Image.open(sys.argv[1])
    dets, annotated = detect_objects(img)
    print(f"偵測到 {len(dets)} 個物品：")
    for d in dets:
        print(d)
    annotated.save("annotated_output.jpg")
    print("標註圖片已存成 annotated_output.jpg")