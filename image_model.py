"""
image_model.py
行李物品辨識模組
"""

import re
import torch
from PIL import Image, ImageDraw
from transformers import (
    AutoProcessor,
    AutoModelForZeroShotObjectDetection,
    Qwen2_5_VLForConditionalGeneration,
)
from qwen_vl_utils import process_vision_info


# =========================
# 1. 模型設定
# =========================

DETECTOR_ID = "IDEA-Research/grounding-dino-tiny"
VLM_ID = "Qwen/Qwen2.5-VL-3B-Instruct"

DEVICE = "cuda" if torch.cuda.is_available() else "cpu"

DETECTION_THRESHOLD = 0.25
TEXT_THRESHOLD = 0.20
MAX_DETECTIONS = 15

# Grounding DINO 會根據這些文字尋找候選物品。
# 後續可以依照專題需求增加、修改。
CANDIDATE_LABELS = [
    "banana",
    "apple",
    "tomato",
    "dried meat",
    "beef jerky",
    "meat jerky",
    "dried beef",
    "dried pork",
    "jerky in a plastic bag",
    "food inside a transparent bag",
    "salami",
    "dried fruit",
    "snack",
    "meat",
    "seafood",
    "vegetable",
    "fruit",
    "water bottle",
    "liquid container",
    "sweater",
    "shirt",
    "jeans",
    "clothing",
    "baseball cap",
    "hat",
    "toiletry bag",
    "toiletries",
    "cream tube",
    "lotion tube",
    "body lotion tube",
    "moisturizer tube",
    "skincare tube",
    "sunscreen tube",
    "cosmetic tube",
    "blue lotion tube",
    "toothpaste tube",
    "wet wipes package",
    "medicine bottle",
    "medicine",
    "medication",
    # 藥品與藥瓶
    "medicine bottle",
    "white medicine bottle",
    "white plastic pill bottle",
    "prescription pill bottle",
    "medication container",
    "pharmacy bottle",
    "bottle with an orange label",
    "vitamin bottle",
    "pill container",
    "medication bottle",
    "pill bottle",
    "prescription medicine bottle",
    "vitamin bottle",
    "pill container",
    "tablets",
    "capsules",
    "pills",
    "plastic bag",
    "food packaging",
    "charger",
    "charging cable",
    "electronic device",
    "suitcase",
]


# =========================
# 2. 延遲載入模型
#    第一次呼叫時載入，之後重複使用
# =========================

_detector = None
_detector_processor = None
_vlm = None
_vlm_processor = None


def load_models():
    global _detector, _detector_processor
    global _vlm, _vlm_processor

    if _detector is None:
        _detector_processor = AutoProcessor.from_pretrained(
            DETECTOR_ID
        )

        _detector = AutoModelForZeroShotObjectDetection.from_pretrained(
            DETECTOR_ID
        ).to(DEVICE)

        _detector.eval()

    if _vlm is None:
        _vlm_processor = AutoProcessor.from_pretrained(VLM_ID)

        dtype = (
            torch.float16
            if DEVICE == "cuda"
            else torch.float32
        )

        _vlm = Qwen2_5_VLForConditionalGeneration.from_pretrained(
            VLM_ID,
            torch_dtype=dtype,
            device_map="auto",
        )

        _vlm.eval()


# =========================
# 3. 使用 Qwen 分析候選物品
# =========================

def classify_crop(crop):
    messages = [
        {
            "role": "user",
            "content": [
                {
                    "type": "image",
                    "image": crop,
                },
                {
                    "type": "text",
                    "text": (
                        "Identify the visible physical object in this "
                        "image crop. Return only one short English noun "
                        "phrase. If the object cannot be identified "
                        "reliably, return unknown. Do not guess hidden "
                        "contents. Do not infer whether an item is legal "
                        "or prohibited."
                    ),
                },
            ],
        }
    ]

    text = _vlm_processor.apply_chat_template(
        messages,
        tokenize=False,
        add_generation_prompt=True,
    )

    image_inputs, video_inputs = process_vision_info(messages)

    inputs = _vlm_processor(
        text=[text],
        images=image_inputs,
        videos=video_inputs,
        padding=True,
        return_tensors="pt",
    ).to(_vlm.device)

    with torch.inference_mode():
        generated = _vlm.generate(
            **inputs,
            max_new_tokens=32,
            do_sample=False,
        )

    # 只取新生成的文字，不包含輸入提示
    generated_trimmed = [
        output[len(input_ids):]
        for input_ids, output in zip(
            inputs.input_ids,
            generated,
        )
    ]

    answer = _vlm_processor.batch_decode(
        generated_trimmed,
        skip_special_tokens=True,
    )[0].strip()

    # 清理成單一名稱，方便組員使用
    label = answer.splitlines()[0].strip()
    label = re.sub(r"""^[\s"'`]+|[\s"'`.,:;]+$""", "", label)
    label = re.sub(r"^(the|a|an)\s+", "", label, flags=re.I)

    if not label or len(label) > 80:
        return "unknown"

    return label.lower()
def classify_food_crop(crop):
    """針對食品區域進行較具體的分類。"""

    messages = [
        {
            "role": "user",
            "content": [
                {
                    "type": "image",
                    "image": crop,
                },
                {
                    "type": "text",
                    "text": (
                        "Classify the visible food in this image. "
                        "Choose the best matching category from: "
                        "beef jerky, pork jerky, salami, sausage, "
                        "dried fruit, other food, uncertain. "
                        "Beef jerky usually appears as irregular, "
                        "flat, dried meat strips. Salami usually "
                        "resembles processed sausage or slices. "
                        "Use visible appearance only. Do not assume "
                        "the contents from the bag or packaging. "
                        "If the image does not provide enough evidence, "
                        "answer uncertain. Return only the category."
                    ),
                },
            ],
        }
    ]

    text = _vlm_processor.apply_chat_template(
        messages,
        tokenize=False,
        add_generation_prompt=True,
    )

    image_inputs, video_inputs = process_vision_info(messages)

    inputs = _vlm_processor(
        text=[text],
        images=image_inputs,
        videos=video_inputs,
        padding=True,
        return_tensors="pt",
    ).to(_vlm.device)

    with torch.inference_mode():
        generated = _vlm.generate(
            **inputs,
            max_new_tokens=20,
            do_sample=False,
        )

    generated_trimmed = [
        output[len(input_ids):]
        for input_ids, output in zip(
            inputs.input_ids, generated
        )
    ]

    answer = _vlm_processor.batch_decode(
        generated_trimmed,
        skip_special_tokens=True,
    )[0].strip().lower()

    answer = answer.splitlines()[0].strip()
    answer = re.sub(r"[\"'`.,:;]+$", "", answer)

    allowed = {
        "beef jerky",
        "pork jerky",
        "salami",
        "sausage",
        "dried fruit",
        "other food",
        "uncertain",
    }

    if answer not in allowed:
        return "uncertain"

    return answer 


def normalize_label(label):
    """統一明顯相同的物品名稱。"""

    label = label.strip().lower()

    aliases = {
        "water bottle": "bottle",
        "plastic water bottle": "bottle",
        "usb-c charger": "charger",
        "charging adapter": "charger",
        "baseball cap": "cap",
    }

    return aliases.get(label, label)

def classify_medicine_crop(crop):
    messages = [
        {
            "role": "user",
            "content": [
                {
                    "type": "image",
                    "image": crop,
                },
                {
                    "type": "text",
                    "text": (
                        "Describe the visible object in this image. "
                        "If it is a bottle containing or intended for "
                        "medicine, return exactly: medicine bottle. "
                        "If it is a vitamin bottle, return exactly: "
                        "vitamin bottle. If it is clearly a different "
                        "object, return its short English object name. "
                        "Do not guess the medicine name or ingredients."
                    ),
                },
            ],
        }
    ]

    text = _vlm_processor.apply_chat_template(
        messages,
        tokenize=False,
        add_generation_prompt=True,
    )

    image_inputs, video_inputs = process_vision_info(messages)

    inputs = _vlm_processor(
        text=[text],
        images=image_inputs,
        videos=video_inputs,
        padding=True,
        return_tensors="pt",
    ).to(_vlm.device)

    with torch.inference_mode():
        generated = _vlm.generate(
            **inputs,
            max_new_tokens=24,
            do_sample=False,
        )

    generated_trimmed = [
        output[len(input_ids):]
        for input_ids, output in zip(
            inputs.input_ids,
            generated,
        )
    ]

    answer = _vlm_processor.batch_decode(
        generated_trimmed,
        skip_special_tokens=True,
    )[0].strip().lower()

    if "vitamin bottle" in answer:
        return "vitamin bottle"

    if "medicine bottle" in answer:
        return "medicine bottle"

    return "unknown"

def calculate_iou(box1, box2):
    """計算兩個框的 IoU（交並比）。"""

    x1 = max(box1[0], box2[0])
    y1 = max(box1[1], box2[1])
    x2 = min(box1[2], box2[2])
    y2 = min(box1[3], box2[3])

    intersection = max(0, x2 - x1) * max(0, y2 - y1)

    area1 = max(0, box1[2] - box1[0]) * max(
        0, box1[3] - box1[1]
    )
    area2 = max(0, box2[2] - box2[0]) * max(
        0, box2[3] - box2[1]
    )

    union = area1 + area2 - intersection

    return intersection / union if union > 0 else 0.0


def remove_duplicate_boxes(candidates, iou_threshold=0.70):
    """保留分數較高、同名稱且高度重疊的候選框。"""

    candidates = sorted(
        candidates,
        key=lambda item: item[1],
        reverse=True,
    )

    kept = []

    for candidate in candidates:
        box, score, label = candidate

        duplicate = False

        for kept_box, kept_score, kept_label in kept:
            if normalize_label(label) != normalize_label(kept_label):
                continue

            if calculate_iou(box, kept_box) >= iou_threshold:
                duplicate = True
                break

        if not duplicate:
            kept.append(candidate)

    return kept


# =========================
# 4. 主要辨識函式
# =========================

def detect_objects(image):
    """
    輸入：
        image: PIL.Image

    回傳：
        detections: [
            {
                "label": str,
                "score": float,
                "box": [x1, y1, x2, y2]
            }
        ]
        annotated_image: PIL.Image
    """

    if not isinstance(image, Image.Image):
        raise TypeError("image 必須是 PIL.Image.Image")

    image = image.convert("RGB")
    annotated_image = image.copy()

    load_models()

    # Grounding DINO 先找出候選物品
    query = ". ".join(CANDIDATE_LABELS) + "."

    inputs = _detector_processor(
        images=image,
        text=query,
        return_tensors="pt",
    ).to(DEVICE)

    with torch.inference_mode():
        outputs = _detector(**inputs)

    results = _detector_processor.post_process_grounded_object_detection(
        outputs,
        inputs.input_ids,
        threshold=DETECTION_THRESHOLD,
        text_threshold=TEXT_THRESHOLD,
        target_sizes=[(image.height, image.width)],
    )

    result = results[0]

    # 依偵測分數排序，限制第一版的 VLM 呼叫數量
    candidates = []

    # 使用文字標籤，避免新版 Transformers 回傳整數類別 ID
    labels = result.get("text_labels", result.get("labels", []))

    image_area = image.width * image.height

    for box, score, label in zip(
          result["boxes"],
          result["scores"],
          labels,
      ):
          x1, y1, x2, y2 = box.tolist()

          box_width = max(0, x2 - x1)
          box_height = max(0, y2 - y1)
          box_area = box_width * box_height

          # 排除覆蓋超過整張圖片 60% 的候選框
          if box_area / image_area > 0.60:
              continue

          candidates.append(
              (
                  box.tolist(),
                  float(score.item()),
                  str(label),
              )
          )

    candidates = remove_duplicate_boxes(candidates)
    candidates = candidates[:MAX_DETECTIONS]

    detections = []
    draw = ImageDraw.Draw(annotated_image)

    for box, score, detector_label in candidates:
        x1, y1, x2, y2 = box

        # 防止座標超出圖片範圍
        x1 = max(0, min(int(x1), image.width - 1))
        y1 = max(0, min(int(y1), image.height - 1))
        x2 = max(x1 + 1, min(int(x2), image.width))
        y2 = max(y1 + 1, min(int(y2), image.height))

        # 適度擴大裁切區域，保留部分包裝與上下文
        margin_x = int((x2 - x1) * 0.08)
        margin_y = int((y2 - y1) * 0.08)

        crop = image.crop((
            max(0, x1 - margin_x),
            max(0, y1 - margin_y),
            min(image.width, x2 + margin_x),
            min(image.height, y2 + margin_y),
        ))

        try:
           # 藥瓶：使用專門的分類提示詞
            if detector_label.strip().lower() in {
                "bottle",
                "medicine bottle",
                "medication bottle",
                "pill bottle",
                "pharmaceutical bottle",
                "vitamin bottle",
            }:
                vlm_label = classify_medicine_crop(crop)
            else:
                vlm_label = classify_crop(crop)
          
        except Exception as exc:
          print(f"Qwen 分析失敗，保留原標籤：{exc}")
          vlm_label = detector_label
        # 不確定時保留偵測模型的原始標籤
        if vlm_label in {"unknown", "uncertain", "other food"}:
            final_label = detector_label
        else:
            final_label = vlm_label

        detections.append({
            "label": final_label,
            "score": round(score, 4),
            "box": [
                x1,
                y1,
                x2,
                y2,
            ],
        })

        draw.rectangle(
            [x1, y1, x2, y2],
            outline="red",
            width=3,
        )

        draw.text(
            (x1, max(0, y1 - 18)),
            f"{final_label} {score:.2f}",
            fill="red",
        )

    return detections, annotated_image
