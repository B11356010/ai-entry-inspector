"""
image_model.py
行李物品辨識模組
"""

import warnings

import torch
from PIL import Image, ImageDraw
from transformers import pipeline


MODEL_NAME = "facebook/detr-resnet-50"

# 延遲載入：第一次呼叫時才載入模型
_detector = None


def _get_detector():
    """載入並重複使用物件偵測模型。"""
    global _detector

    if _detector is None:
        device = 0 if torch.cuda.is_available() else -1

        _detector = pipeline(
            task="object-detection",
            model=MODEL_NAME,
            device=device,
        )

    return _detector


def detect_objects(image):
    """
    輸入：
        image: PIL Image

    回傳：
        detections: list[dict]
        annotated_image: PIL Image

    辨識失敗時回傳空清單及原圖副本。
    """

    if not isinstance(image, Image.Image):
        raise TypeError("image 必須是 PIL Image 物件")

    # 保留原圖，並統一使用 RGB 格式
    annotated_image = image.convert("RGB").copy()
    detections = []

    try:
        detector = _get_detector()
        results = detector(annotated_image)

        draw = ImageDraw.Draw(annotated_image)

        for item in results:
            box = item["box"]

            x1 = max(0, min(image.width, round(box["xmin"])))
            y1 = max(0, min(image.height, round(box["ymin"])))
            x2 = max(0, min(image.width, round(box["xmax"])))
            y2 = max(0, min(image.height, round(box["ymax"])))

            if x2 <= x1 or y2 <= y1:
                continue

            label = str(item["label"])
            score = float(item["score"])

            detections.append({
                "label": label,
                "score": score,
                "box": [x1, y1, x2, y2],
            })

            draw.rectangle(
                [x1, y1, x2, y2],
                outline="red",
                width=3,
            )

            draw.text(
                (x1, max(0, y1 - 18)),
                f"{label} {score:.2f}",
                fill="red",
            )

        return detections, annotated_image

    except Exception as e:
        warnings.warn(
            f"物品辨識失敗：{type(e).__name__}: {e}",
            RuntimeWarning,
        )

        # 維持兩個回傳值，避免主程式解包失敗
        return [], annotated_image

