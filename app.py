from image_model import recognize_image
import streamlit as st
from PIL import Image
from image_model import recognize_image

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
    
    with st.spinner("AI 正在分析照片，首次執行可能需要較久時間..."):
        try:
            results = recognize_image(image)
    
            if not results:
                st.warning("AI 沒有找到可顯示的辨識結果，請換一張照片。")
            else:
                # 取出最有可能的辨識結果
                best = results[0]
                label = best["label"]
                score = best["score"]
    
                # 將信心分數轉換成容易理解的提示
                if score >= 0.80:
                    message = "AI 很有把握，但仍需確認物品是否辨識正確。"
                elif score >= 0.50:
                    message = "AI 有一定把握，建議再確認物品種類。"
                else:
                    message = "AI 不太確定，建議重新拍照或人工確認。"
    
                st.markdown("### 最可能的辨識結果")
                st.write(f"**物品名稱：** {label}")
                st.write(f"**AI 信心分數：** {score:.1%}")
    
                if score >= 0.80:
                    st.success(message)
                elif score >= 0.50:
                    st.info(message)
                else:
                    st.warning(message)
    
                # 顯示信心分數長條
                st.progress(float(max(0, min(1, score))))
    
                # 顯示其他候選結果
                with st.expander("查看其他辨識候選"):
                    for i, item in enumerate(results[1:], start=2):
                        st.write(
                            f"{i}. {item['label']} "
                            f"（信心分數：{item['score']:.1%}）"
                        )
    
                st.caption(
                    "注意：信心分數是模型對候選類別的分數，"
                    "不等於實際辨識正確率，也不能用來判定能否入境台灣。"
                )
    
        except Exception:
            st.error("目前無法完成辨識，請稍後再試。")
    
    st.subheader("📋 入境規定提醒")
    st.write(
        "請依照辨識出的物品種類，進一步確認台灣官方入境及檢疫規定。"
    )


else:
    st.caption("請先上傳照片，開始測試系統。")

st.divider()

st.caption("課程期末專題｜AI 入境物品檢查系統")
