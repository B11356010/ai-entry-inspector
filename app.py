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

            "選擇要進一步查核的物品",
            options=[item[0] for item in labels],
            key="selected_detection_display",
        )
        selected_label = next(label for display, label in labels if display == selected_display)
        st.session_state.selected_item = selected_label

        st.write("請另外拍攝或上傳該物品的成分、產地或商品標籤照片。")
        label_file = st.file_uploader(
            "上傳物品標籤照片（可略過，改用下方手動輸入）",
            type=["jpg", "jpeg", "png", "webp"],
            key="label_uploader",
        )

        if label_file is not None:
            try:
                label_image = safe_image(label_file)
                st.image(label_image, caption="已上傳的標籤照片", use_container_width=True)

                if st.button("🔤 辨識標籤文字（OCR）", use_container_width=True):
                    with st.spinner("正在辨識標籤文字，第一次執行可能需要載入 OCR 模型……"):
                        try:
                            from ocr_model import recognize_text, get_full_text

                            ocr_lines, ocr_annotated = recognize_text(label_image)
                            full_text = get_full_text(ocr_lines)

                            # ui_components.render_ocr_results 接受 dict；
                            # OCR 模組實際回傳 (list, annotated_image)，在此轉成相容格式。
                            st.session_state.ocr_result = {
                                "success": bool(full_text.strip()),
                                "text": full_text,
                                "lines": ocr_lines,
                                "message": "" if full_text.strip() else "沒有辨識到文字",
                            }
                            st.session_state.ocr_annotated_image = ocr_annotated
                            st.session_state.ocr_text = full_text
                            st.session_state.regulation_result = None
                        except Exception as exc:
                            st.error(f"OCR 執行失敗：{type(exc).__name__}: {exc}")
                            st.exception(exc)

                if st.session_state.ocr_annotated_image is not None:
                    st.image(
                        st.session_state.ocr_annotated_image,
                        caption="OCR 文字位置標註圖",
                        use_container_width=True,
                    )
            except Exception as exc:
                st.error(f"標籤圖片讀取失敗：{type(exc).__name__}: {exc}")

        if st.session_state.ocr_result is not None:
            edited_ocr_text = render_ocr_results(st.session_state.ocr_result)
            st.session_state.ocr_text = edited_ocr_text

    else:
        st.warning("目前沒有可供選擇的辨識項目。")
else:
    st.info("請先完成第一階段的行李物品辨識，這裡才會出現可選擇的物品。")

# -------------------------
# 3. 法規查核
# -------------------------
st.divider()
st.header("③ 入境規定初步查核")

if st.session_state.selected_item:
    st.write(f"目前選擇的物品：**{st.session_state.selected_item}**")

    with st.form("regulation_check_form"):
        st.markdown("請依照商品標籤或旅客提供的資訊補充資料。OCR 文字會先帶入成分/標籤欄位，可自行修正。")

        item_name = st.text_input(
            "物品名稱",
            value=str(st.session_state.selected_item),
        )
        ingredients = st.text_area(
            "成分／標籤文字",
            value=st.session_state.ocr_text,
            height=120,
            help="可貼上或修改 OCR 辨識出的文字；若沒有標籤，也可以填寫已知資訊。",
        )
        origin = st.text_input("產地／原產國", placeholder="例如：日本；不清楚可填「不明」")
        quantity = st.text_input("攜帶數量", placeholder="例如：2 包、500 公克")
        purpose = st.text_input("攜帶目的", placeholder="例如：個人自用、送禮")

        submitted = st.form_submit_button(
            "📋 查詢入境規定",
            type="primary",
            use_container_width=True,
        )

    if submitted:
        item_info = {
            "name": item_name.strip(),
            "ingredients": ingredients.strip(),
            "origin": origin.strip(),
            "quantity": quantity.strip(),
            "purpose": purpose.strip(),
        }

        with st.spinner("正在比對專案內的法規規則資料……"):
            try:
                from regulation_checker import check_regulations

                st.session_state.regulation_result = check_regulations(item_info)
            except Exception as exc:
                st.session_state.regulation_result = {
                    "status": "insufficient_info",
                    "summary": "法規查詢程式執行失敗。",
                    "reasons": [f"{type(exc).__name__}: {exc}"],
                    "sources": [],
                    "missing_info": [],
                }

    if st.session_state.regulation_result is not None:
        render_regulation_result(st.session_state.regulation_result)

    st.caption(
        "查核結果來自專案內的 data/regulation_rules.json 規則資料。"
        "若資料未建立、內容不完整或未命中規則，系統不能據此認定物品可以入境。"
    )
else:
    st.info("請先完成物品辨識並選擇一項物品，再進行法規查核。")

# -------------------------
# 頁尾
# -------------------------
