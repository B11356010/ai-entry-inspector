"""
ocr_model.py
標籤文字辨識（OCR）模組

使用 EasyOCR 辨識商品標籤、包裝上的文字（繁體中文 + 英文），
供後續 regulation_checker.py 比對入境規定使用。

主要函式：
    recognize_text(image)  -> (results, annotated_image)
    get_full_text(results) -> str
"""

import warnings

import numpy as np
from PIL import Image, ImageDraw, ImageFont


# EasyOCR 規定：繁體中文 ch_tra 只能與英文 en 搭配
OCR_LANGUAGES = ["ch_tra", "en"]

# 低於此信心分數的文字視為雜訊，不回傳
DEFAULT_MIN_SCORE = 0.3

# 圖片最長邊上限（像素），太大的照片先縮小以加快辨識
MAX_IMAGE_SIDE = 1600

# 延遲載入：第一次呼叫時才載入模型
_reader = None


def _get_reader():
    """載入並重複使用 EasyOCR 模型。"""
    global _reader

    if _reader is None:
        import easyocr  # 放在這裡，避免沒用到 OCR 時拖慢 app 啟動
        import torch

        _reader = easyocr.Reader(
            OCR_LANGUAGES,
            gpu=torch.cuda.is_available(),
            verbose=False,
        )

    return _reader


def _resize_if_needed(image):
    """若圖片太大則等比例縮小，回傳 (縮放後圖片, 縮放倍率)。"""
    longest = max(image.width, image.height)

    if longest <= MAX_IMAGE_SIDE:
        return image, 1.0

    scale = MAX_IMAGE_SIDE / longest
    new_size = (round(image.width * scale), round(image.height * scale))
    return image.resize(new_size, Image.LANCZOS), scale


def recognize_text(image, min_score=DEFAULT_MIN_SCORE):
    """
    輸入：
        image: PIL Image
        min_score: 最低信心分數（0~1），低於此值的結果會被過濾

    回傳：
        results: list[dict]，依閱讀順序（由上到下、由左到右）排列
            {
                "text": str,          辨識出的文字
                "score": float,       信心分數 0~1
                "box": [x1, y1, x2, y2]  在原圖上的座標
            }
        annotated_image: PIL Image，用綠框與編號標出文字位置

    辨識失敗時回傳空清單及原圖副本。
    """

    if not isinstance(image, Image.Image):
        raise TypeError("image 必須是 PIL Image 物件")

    # 保留原圖，並統一使用 RGB 格式
    annotated_image = image.convert("RGB").copy()
    results = []

    try:
        reader = _get_reader()

        small_image, scale = _resize_if_needed(annotated_image)
        raw_results = reader.readtext(np.array(small_image))

        for points, text, score in raw_results:
            text = str(text).strip()
            score = float(score)

            if not text or score < min_score:
                continue

            # EasyOCR 回傳四個角點，轉成 [x1, y1, x2, y2] 並換算回原圖座標
            xs = [p[0] / scale for p in points]
            ys = [p[1] / scale for p in points]

            x1 = max(0, min(image.width, round(min(xs))))
            y1 = max(0, min(image.height, round(min(ys))))
            x2 = max(0, min(image.width, round(max(xs))))
            y2 = max(0, min(image.height, round(max(ys))))

            if x2 <= x1 or y2 <= y1:
                continue

            results.append({
                "text": text,
                "score": score,
                "box": [x1, y1, x2, y2],
            })

        # 依閱讀順序排序：先分行（約 20px 為一行），再由左到右
        results.sort(key=lambda r: (r["box"][1] // 20, r["box"][0]))

        draw = ImageDraw.Draw(annotated_image)

        # 編號字體大小隨圖片大小調整（Pillow 10.1 以上才支援 size 參數）
        font_size = max(16, max(image.width, image.height) // 60)
        try:
            font = ImageFont.load_default(size=font_size)
        except TypeError:
            font = ImageFont.load_default()

        for index, item in enumerate(results, start=1):
            x1, y1, x2, y2 = item["box"]

            draw.rectangle(
                [x1, y1, x2, y2],
                outline="lime",
                width=3,
            )

            # 預設字型不支援中文，所以框上只標編號，文字內容由 app 另外列出
            draw.text(
                (x1, max(0, y1 - font_size - 4)),
                str(index),
                fill="lime",
                font=font,
            )

        return results, annotated_image

    except Exception as e:
        warnings.warn(
            f"文字辨識失敗：{type(e).__name__}: {e}",
            RuntimeWarning,
        )

        # 維持兩個回傳值，避免主程式解包失敗
        return [], annotated_image


def get_full_text(results, separator="\n"):
    """
    把 recognize_text() 的結果合併成一段文字，
    方便給 regulation_checker 做關鍵字比對。
    """
    return separator.join(item["text"] for item in results)


if __name__ == "__main__":
    # 本機測試用：python ocr_model.py 圖片路徑
    import sys

    if len(sys.argv) < 2:
        print("用法：python ocr_model.py <圖片路徑>")
        sys.exit(1)

    img = Image.open(sys.argv[1])
    texts, annotated = recognize_text(img)

    print(f"共辨識到 {len(texts)} 段文字：")
    for i, t in enumerate(texts, start=1):
        print(f"{i}. {t['text']}（信心分數：{t['score']:.1%}）")

    annotated.save("ocr_result.png")
    print("標註圖已存成 ocr_result.png")