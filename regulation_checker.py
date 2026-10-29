
import json
from pathlib import Path


DATA_FILE = Path(__file__).parent / "data" / "regulation_rules.json"


def check_regulations(item_info):
    """依據物品資訊查找相關入境規定。"""

    result = {
        "status": "insufficient_info",
        "summary": "資訊不足，無法做出可靠判定。",
        "reasons": [],
        "sources": [],
        "missing_info": []
    }

    # 1. 檢查輸入格式
    if not isinstance(item_info, dict):
        result["reasons"].append("輸入資料必須是字典。")
        return result

    # 2. 檢查必要欄位
    required_fields = [
        "name", "ingredients", "origin", "quantity", "purpose"
    ]

    for field in required_fields:
        value = item_info.get(field)

        if value is None:
            result["missing_info"].append(field)
        elif isinstance(value, str):
            if not value.strip() or value.strip().casefold() in {
                "unknown", "不明", "未知"
            }:
                result["missing_info"].append(field)

    result["missing_info"] = list(
        dict.fromkeys(result["missing_info"])
    )
    name = item_info.get("name")
    ingredients = item_info.get("ingredients")

    # 3. 讀取規則資料
    try:
        with DATA_FILE.open("r", encoding="utf-8") as file:
            rules = json.load(file)
        if not isinstance(rules, list):
            raise ValueError("規則資料必須是清單")

    except (OSError, json.JSONDecodeError, ValueError):
        result["summary"] = "規則資料無法讀取，暫時無法查詢。"
        result["reasons"].append("請檢查規則檔案是否存在及格式是否正確。")
        return result
    # 4. 比對物品名稱與成分
    name_text = str(name or "").casefold()
    ingredients_text = str(ingredients or "").casefold()
    text = f"{name_text} {ingredients_text}"

    matched_rules = []
    matched_product_types = []

    for rule in rules:
        if not isinstance(rule, dict):
            continue

    # 原有法規關鍵字比對
        keywords = rule.get("keywords", [])

        if isinstance(keywords, list):
            matched_keywords = [
                keyword
                for keyword in keywords
                if isinstance(keyword, str)
                and keyword
                and keyword.casefold() in text
            ]

            if matched_keywords:
                matched_rules.append(rule)

        # 商品分類關鍵字比對
        product_types = rule.get("product_types", {})

        if not isinstance(product_types, dict):
            continue

        for product_id, product_info in product_types.items():
            if not isinstance(product_info, dict):
                continue

            product_keywords = product_info.get("keywords", [])

            if not isinstance(product_keywords, list):
                continue

            if any(
                isinstance(keyword, str)
                and keyword
                and keyword.casefold() in name_text
                for keyword in product_keywords
            ):
                matched_product_types.append({
                    "id": product_id,
                    "name": product_info.get("name")
                })

                # 商品分類命中時，也將所屬法規規則加入結果
                if rule not in matched_rules:
                    matched_rules.append(rule)
    # 5. 整理官方來源
    for rule in matched_rules:
    # 先收集主要來源
        sources = [{
        "title": rule.get("source_title"),
        "url": rule.get("source_url")
    }]

    # 再收集額外來源
        additional_sources = rule.get("additional_sources", [])
        if isinstance(additional_sources, list):
            sources.extend(
            source for source in additional_sources
            if isinstance(source, dict)
            )

    # 檢查來源格式
        for source in sources:
            title = source.get("title")
            url = source.get("url")

            if (
                isinstance(title, str)
                and isinstance(url, str)
                and url.startswith("https://")
            ):
                source_item = {
                    "title": title,
                    "url": url
                }

                if source_item not in result["sources"]:
                    result["sources"].append(source_item)

    # 6. 決定初步結果
    if matched_rules and result["sources"]:
        result["status"] = "needs_review"
        result["summary"] = "已找到相關規定，仍須確認適用條件。"
        result["reasons"].append(
            "找到相關規則，但關鍵字比對不能直接判定是否允許入境。"
        )
    elif result["missing_info"]:
        result["status"] = "insufficient_info"
        result["summary"] = "物品資訊不足，無法可靠查詢。"
        result["reasons"].append("請補充缺少的物品資訊。")
    else:
        result["status"] = "insufficient_info"
        result["summary"] = "查無可用的相關規則，無法可靠判定。"
        result["reasons"].append(
            "未找到可用的相關規則，不代表允許入境。"
        )
    result["matched_product_types"] = matched_product_types
    return result
