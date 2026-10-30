"""
app.py
AI 入境物品檢查系統 - Streamlit 本地端主程式

流程：
1. 上傳行李照片並執行物品辨識
2. 選擇要進一步查核的物品
3. 上傳該物品標籤照片並執行 OCR
4. 編輯/補充物品資訊後查詢本地法規規則
"""

import streamlit as st
from PIL import Image

st.set_page_config(
    page_title="AI 入境物品檢查系統",
    page_icon="🧳",
    layout="wide",
)

# UI 模組只負責顯示結果
from ui_components import (
    render_detection_results,
    render_ocr_results,
    render_regulation_result,
)


def init_state():
    defaults = {
        "detections": [],
        "annotated_image": None,
        "detected_image_name": None,
        "ocr_result": None,
        "ocr_annotated_image": None,
        "ocr_text": "",
        "regulation_result": None,
        "selected_item": None,
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


def reset_after_new_luggage():
    st.session_state.detections = []
    st.session_state.annotated_image = None
    st.session_state.detected_image_name = None
    st.session_state.ocr_result = None
    st.session_state.ocr_annotated_image = None
    st.session_state.ocr_text = ""
    st.session_state.regulation_result = None
    st.session_state.selected_item = None


def safe_image(uploaded_file):
    """將 Streamlit 上傳檔轉成 RGB PIL Image。"""
    return Image.open(uploaded_file).convert("RGB")


init_state()

# -------------------------
# 頁面標題
# -------------------------
st.title("🧳 AI 入境物品檢查系統")
st.caption("行李物品辨識・標籤文字擷取・台灣入境規定提醒")

st.info(
    "本系統為專題展示與初步查詢工具。AI 辨識及關鍵字比對可能有誤，"
    "不代表海關核准或正式法律判定；請以主管機關最新公告及現場查驗為準。"
)

with st.sidebar:
    st.header("使用流程")
    st.markdown(
        "1. 上傳行李照片\n"
        "2. 執行 AI 物品辨識\n"
        "3. 選擇需要查核的物品\n"
        "4. 上傳標籤照片並執行 OCR\n"
        "5. 補充資料並查詢規定"
    )
    st.divider()
    st.caption("本地端執行：請保持啟動 Streamlit 的終端機開啟。")

# -------------------------
# 1. 行李照片與物品辨識
# -------------------------
st.header("① 行李物品辨識")

luggage_file = st.file_uploader(
    "請上傳行李照片",
    type=["jpg", "jpeg", "png", "webp"],
    key="luggage_uploader",
    help="建議使用光線充足、物品盡量分開且清楚可見的照片。",
)
