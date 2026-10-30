"""
ui_components.py
網站介面元件（Streamlit）

負責人：黃亭瑜

固定函式（名稱與參數不可任意更改）：
    render_detection_results(detections, annotated_image)
    render_ocr_results(ocr_result)
    render_regulation_result(regulation_result)

原則：
    - 只負責「顯示」資料，不載入 AI 模型、不重新查詢法規。
    - 輸入是 None、空值或格式不對時，顯示提示訊息，不讓程式崩潰。
    - 信心分數只是模型自評，不是實際準確率。
    - AI 偵測結果不是法規結論，法規結論以 check_regulations() 與官方公告為準。
"""

import streamlit as st


# ---------------------------------------------------------------------------
# 共用小工具
# ---------------------------------------------------------------------------

def _get(data, *keys, default=None):
    """從字典中依序找第一個存在且不是 None 的欄位。

    因為 OCR 與法規模組的欄位名稱可能微調，這裡容許幾種常見寫法，
    正式欄位名稱請以組員的回傳規格為準。
    """
    if not isinstance(data, dict):
        return default
    for key in keys:
        if key in data and data[key] is not None:
            return data[key]
    return default


def _manual_check_notice():
    """人工確認提醒。"""
    st.info(
        "🧑‍✈️ 本系統結果僅供參考，請以人工確認及現場海關判定為準。"
    )


# DETR 模型英文標籤 -> 中文（常見行李物品，可再擴充）
LABEL_ZH = {
    "bottle": "瓶子", "wine glass": "酒杯", "cup": "杯子",
    "banana": "香蕉", "apple": "蘋果", "orange": "柳橙",
    "sandwich": "三明治", "broccoli": "花椰菜", "carrot": "紅蘿蔔",
    "hot dog": "熱狗", "pizza": "披薩", "donut": "甜甜圈", "cake": "蛋糕",
    "book": "書", "cell phone": "手機", "laptop": "筆記型電腦",
    "scissors": "剪刀", "knife": "刀子", "backpack": "背包",
    "handbag": "手提包", "suitcase": "行李箱", "umbrella": "雨傘",
    "toothbrush": "牙刷", "hair drier": "吹風機", "teddy bear": "玩偶",
    "clock": "時鐘", "vase": "花瓶", "potted plant": "盆栽植物",
}

# 法規判定狀態 -> (顯示文字, 圖示, Streamlit 顏色)
STATUS_STYLE = {
    "allowed":    ("可攜帶入境", "✅", "green"),
    "declare":    ("需申報 / 進一步查核", "⚠️", "orange"),
    "prohibited": ("禁止攜帶入境", "⛔", "red"),
    "unknown":    ("無法判斷，請人工確認", "❔", "gray"),
}


# ---------------------------------------------------------------------------
# 1. 物品辨識結果
# ---------------------------------------------------------------------------

def render_detection_results(detections, annotated_image):
    """顯示物品辨識結果。

    參數：
        detections: list[dict]，每筆 {"label": str, "score": float, "box": [x1, y1, x2, y2]}
        annotated_image: PIL Image，畫好方框的圖片
    """
    st.subheader("🔍 物品辨識結果")

    # 標註後照片
    if annotated_image is not None:
        try:
            st.image(
                annotated_image,
                caption="標註後照片（方框為 AI 偵測到的物品）",
                use_container_width=True,
            )
        except Exception as e:
            st.error(f"標註圖片無法顯示：{e}")
    else:
        st.warning("沒有收到標註後的圖片。")

    # 物品清單
    if not isinstance(detections, list) or len(detections) == 0:
        st.warning(
            "沒有偵測到物品。請嘗試更清楚、光線更好、物品不互相遮擋的照片。"
            "未偵測到不代表行李內沒有受管制物品。"
        )
        return

    rows = []
    for item in detections:
        if not isinstance(item, dict):
            continue
        label = str(item.get("label", "未知"))
        try:
            score = f"{float(item.get('score', 0)):.1%}"
        except (TypeError, ValueError):
            score = "—"
        rows.append({
            "物品": LABEL_ZH.get(label, label),
            "英文標籤": label,
            "模型信心分數": score,
        })

    if not rows:
        st.warning("辨識資料格式不正確，無法顯示物品清單。")
        return

    st.success(f"共偵測到 {len(rows)} 個物品")
    st.dataframe(rows, use_container_width=True, hide_index=True)
    st.caption(
        "「模型信心分數」是模型對自己判斷的把握程度，不等於實際準確率；"
        "偵測到物品也不代表該物品違規。"
    )


# ---------------------------------------------------------------------------
# 2. OCR 結果
# ---------------------------------------------------------------------------

def render_ocr_results(ocr_result):
    """顯示 OCR 標籤文字辨識結果，並提供可編輯欄位。

    參數：
        ocr_result: dict，extract_text() 的回傳值

    回傳：
        str，使用者確認 / 修改後的文字（沒有文字時回傳空字串）
    """
    st.subheader("🏷️ 標籤文字辨識（OCR）")

    if not isinstance(ocr_result, dict):
        st.error("OCR 結果格式不正確或沒有回傳資料。")
        _manual_check_notice()
        return ""

    success = _get(ocr_result, "success", "ok", default=True)
    error = _get(ocr_result, "error", "message", "error_message")
    text = _get(ocr_result, "text", "full_text", default="")
    lines = _get(ocr_result, "lines", "texts", default=[])

    if isinstance(text, (list, tuple)):
        text = "\n".join(str(t) for t in text)
    if not text and isinstance(lines, (list, tuple)):
        text = "\n".join(
            str(_get(line, "text", default=line)) if isinstance(line, dict) else str(line)
            for line in lines
        )
    text = str(text or "").strip()

    if success is False or error:
        st.error(f"OCR 辨識失敗：{error or '未知錯誤'}")

    if not text:
        st.info("沒有辨識到文字。可在下方手動輸入標籤上的文字。")

    edited = st.text_area(
        "辨識文字（可自行修正後再查詢）",
        value=text,
        height=150,
        key="ocr_text_input",
    )

    confidence = _get(ocr_result, "confidence", "score")
    if confidence is not None:
        try:
            st.caption(f"OCR 模型信心分數：{float(confidence):.1%}（不等於實際準確率）")
        except (TypeError, ValueError):
            pass

    st.caption("OCR 可能認錯字，特別是手寫、反光或小字，請務必人工核對。")
    return edited


# ---------------------------------------------------------------------------
# 3. 法規查詢結果
# ---------------------------------------------------------------------------

def _render_one_rule(result):
    """顯示單一物品的法規判定。"""
    item = _get(result, "item", "item_name", "name", default="未知物品")
    status = str(_get(result, "status", "result", default="unknown")).lower()
    reason = _get(result, "reason", "description", "message")
    sources = _get(result, "sources", "source_urls", "source_url", "source", "url", default=[])

    text, icon, color = STATUS_STYLE.get(status, STATUS_STYLE["unknown"])

    with st.container(border=True):
        st.markdown(f"**{icon} {item}**　:{color}[{text}]")

        if reason:
            st.write(f"理由：{reason}")

        # 官方來源（可以是字串、字串清單，或 {"title", "url"} 清單）
        if isinstance(sources, (str, dict)):
            sources = [sources]
        links = []
        for s in sources or []:
            if isinstance(s, dict):
                url = _get(s, "url", "link")
                title = _get(s, "title", "name", default=url)
            else:
                url, title = str(s), str(s)
            if url and str(url).startswith("http"):
                links.append(f"- [{title}]({url})")
            elif title:
                links.append(f"- {title}")

        if links:
            st.markdown("官方來源：\n" + "\n".join(links))
        else:
            st.caption("⚠️ 此判定沒有附上官方來源，請自行查證。")


def render_regulation_result(regulation_result):
    """顯示入境規定查詢結果。

    參數：
        regulation_result: dict，check_regulations() 的回傳值。
            可以是單一物品的結果，也可以是含 "results" / "items" 清單的總結果。
    """
    st.subheader("📋 入境規定查詢結果")

    if not isinstance(regulation_result, dict):
        st.error("法規查詢結果格式不正確或沒有回傳資料。")
        _manual_check_notice()
        return

    error = _get(regulation_result, "error", "error_message")
    if error or _get(regulation_result, "success", default=True) is False:
        st.error(f"法規查詢失敗：{error or '未知錯誤'}")

    results = _get(regulation_result, "results", "items")
    if results is None:
        # 單一物品結果
        results = [regulation_result] if _get(regulation_result, "item", "item_name", "name", "status") else []

    if not isinstance(results, list) or not results:
        st.info("沒有可顯示的法規查詢結果。")
        _manual_check_notice()
        return

    # 依嚴重程度排序：禁止 > 需申報 > 無法判斷 > 可攜帶
    order = {"prohibited": 0, "declare": 1, "unknown": 2, "allowed": 3}
    results = sorted(
        [r for r in results if isinstance(r, dict)],
        key=lambda r: order.get(str(_get(r, "status", "result", default="unknown")).lower(), 2),
    )

    for r in results:
        _render_one_rule(r)

    _manual_check_notice()
