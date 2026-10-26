
from transformers import pipeline

# 載入已經訓練好的影像辨識模型
classifier = pipeline(
    "image-classification",
    model="google/vit-base-patch16-224"
)

def recognize_image(image):
    """辨識照片，回傳最可能的物品類別。"""
    results = classifier(image)

    # 取出最可能的前三個類別
    return [
        {
            "label": item["label"],
            "score": item["score"]
        }
        for item in results[:3]
    ]
