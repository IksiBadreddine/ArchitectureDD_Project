import requests
from bs4 import BeautifulSoup
import json
from datetime import datetime
import os

#URL = "https://fr.hespress.com/?utm_source=hespress_ar&utm_medium=web"
#URL = "https://en.hespress.com/"
URL="https://www.avito.ma/fr/maroc/voitures"

def scrape_hespress():

    headers = {
        "User-Agent": "Mozilla/5.0"
    }

    response = requests.get(URL, headers=headers)

    print("STATUS CODE:", response.status_code)

    soup = BeautifulSoup(response.text, "html.parser")

    articles = []

    # 🔥 stratégie : récupérer tous les liens
    links = soup.find_all("a")

    print("TOTAL LINKS FOUND:", len(links))

    for link in links:

        title = link.get_text(strip=True)
        href = link.get("href")

        # filtre basique (évite menu/footer)
        if href and title and len(title) > 30:

            articles.append({
                "title": title,
                "url": href,
                "source": "Hespress",
                "scraped_at": str(datetime.now())
            })

        if len(articles) >= 10:
            break

    print("SCRAPED ARTICLES:", len(articles))

    return articles


def save_to_bronze(data):
    folder = "data/bronze"
    os.makedirs(folder, exist_ok=True)

    file_path = f"{folder}/articles_{datetime.now().date()}.json"

    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

    print("Saved to:", file_path)


if __name__ == "__main__":
    data = scrape_hespress()
    save_to_bronze(data)