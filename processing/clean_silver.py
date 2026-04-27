import json
import os
import re
from datetime import datetime
from urllib.parse import urlparse


# ----------------------------
# 1. CLEAN TITLE
# ----------------------------
def clean_title(title: str):

    # enlever espaces inutiles
    title = title.strip()

    # enlever caractères spéciaux inutiles
    title = re.sub(r"\s+", " ", title)

    return title


# ----------------------------
# 2. EXTRACT TIME IF EXISTS
# ----------------------------
def extract_time(title: str):
    match = re.match(r"^(\d{1,2}:\d{2})(.*)", title)

    if match:
        return match.group(1), match.group(2).strip()

    return None, title


# ----------------------------
# 3. SIMPLE CATEGORY DETECTION
# ----------------------------
def detect_category(title: str):

    title = title.lower()

    if any(word in title for word in ["morocco", "casablanca", "rabat"]):
        return "local"

    if any(word in title for word in ["football", "psg", "hakimi"]):
        return "sports"

    if any(word in title for word in ["minister", "king", "political", "government"]):
        return "politics"

    if any(word in title for word in ["weather", "storm", "hail"]):
        return "weather"

    return "international"


# ----------------------------
# 4. LOAD BRONZE
# ----------------------------
def load_bronze(file_path):
    with open(file_path, "r", encoding="utf-8") as f:
        return json.load(f)


# ----------------------------
# 5. TRANSFORM TO SILVER
# ----------------------------
def transform_to_silver(data):

    silver_data = []

    for item in data:

        raw_title = item.get("title", "")

        # 1. extract time
        time, clean_part = extract_time(raw_title)

        # 2. clean title
        clean_part = clean_title(clean_part)

        # 3. category detection
        category = detect_category(clean_part)

        # 4. validate URL
        url = item.get("url", "")
        domain = urlparse(url).netloc if url else None

        silver_data.append({
            "original_title": raw_title,
            "title": clean_part,
            "time": time,
            "url": url,
            "domain": domain,
            "source": item.get("source"),
            "category": category,
            "scraped_at": item.get("scraped_at"),
            "processed_at": str(datetime.now())
        })

    return silver_data


# ----------------------------
# 6. SAVE SILVER
# ----------------------------
def save_silver(data):

    os.makedirs("data/silver", exist_ok=True)

    file_path = "data/silver/silver_articles.json"

    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

    print("✅ SILVER SAVED ->", file_path)


# ----------------------------
# 7. RUN PIPELINE
# ----------------------------
if __name__ == "__main__":

    bronze_path = "data/bronze/articles_2026-04-27.json"

    bronze_data = load_bronze(bronze_path)

    silver_data = transform_to_silver(bronze_data)

    save_silver(silver_data)

    print("TOTAL SILVER RECORDS:", len(silver_data))