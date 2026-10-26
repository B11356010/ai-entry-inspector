from image_model import recognize_image
import streamlit as st
from PIL import Image
from image_model import detect_objects

st.set_page_config(
    page_title="AI 入境物品檢查",
    page_icon="🧳",
    layout="centered"
)

st.title("🧳 AI 入境物品檢查")
st.write(
    "上傳打開的行李箱照片，"
    "讓 AI 嘗試辨識其中的物品。"
)

st.info(
    "目前是第一階段測試版："
    "先辨識常見物品，尚未判斷物品能否攜帶入境台灣。"
)

uploaded_file = st.file_uploader(
    "請上傳行李箱照片",
    type=["jpg", "jpeg", "png"]
)

if uploaded_file is not None:
    image = Image.open(uploaded_file).convert("RGB")

    st.subheader("原始照片")
    st.image(image, use_container_width=True)

    if st.button("開始辨識物品", type="primary"):
        with st.spinner("AI 正在辨識，第一次載入模型可能需要較久……"):
            try:
                detections, annotated_image = detect_objects(image)

                st.subheader("AI 辨識結果")
                st.image(
                    annotated_image,
                    caption="方框表示 AI 偵測到的物品",
                    use_container_width=True
                )

                if detections:
                    st.success(
                        f"共偵測到 {len(detections)} 個物品"
                    )

                    for index, item in enumerate(detections, start=1):
                        st.write(
                            f"{index}. {item['label']} "
                            f"（信心分數：{item['score']:.1%}）"
                        )
                else:
                    st.warning(
                        "沒有偵測到物品，"
                        "請嘗試更清楚、光線更好的照片。"
                    )

                st.warning(
                    "注意：辨識結果可能錯誤或漏掉物品。"
                    "偵測到物品不代表它違規，"
                    "未偵測到也不代表行李內沒有受管制物品。"
                )

            except Exception as e:
                st.error(
                    "辨識失敗，請稍後再試。"
                    f"錯誤訊息：{e}"
                )
