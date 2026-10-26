from image_model import recognize_image
import streamlit as st
from PIL import Image

st.set_page_config(
    page_title="AI 入境物品檢查系統",
    page_icon="🧳",
    layout="centered"
)

st.title("🧳 AI 入境物品檢查系統")

st.write(
    "上傳物品照片，協助辨識物品，"
    "並查詢外國旅客入境台灣的相關規定。"
)

st.info(
    "目前為開發測試版。辨識結果僅供參考，"
    "不能取代海關或檢疫機關的正式判定。"
)

st.subheader("📷 上傳物品照片")

uploaded_file = st.file_uploader(
    "請選擇一張物品照片",
    type=["jpg", "jpeg", "png"]
)

if uploaded_file is not None:
    image = Image.open(uploaded_file).convert("RGB")

    st.image(
        image,
        caption="你上傳的物品照片",
        use_container_width=True
    )

    st.success("照片上傳成功！")

    st.subheader("🔍 AI 辨識結果")
    st.write("下一步將在這裡加入 AI 影像辨識模型。")

    st.subheader("📋 入境規定提醒")
    st.write("辨識物品後，系統將顯示相關官方規定。")

else:
    st.caption("請先上傳照片，開始測試系統。")

st.divider()

st.caption(
    "課程期末專題｜AI 入境物品檢查系統"
)
