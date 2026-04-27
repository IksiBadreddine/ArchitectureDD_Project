import requests
from bs4 import BeautifulSoup
from datetime import datetime
import time

HEADERS = {"User-Agent": "Mozilla/5.0"}


# ---------------------------
# 1. GET LIST LINKS
# ---------------------------
def get_links(list_url):
    r = requests.get(list_url, headers=HEADERS)
    soup = BeautifulSoup(r.text, "html.parser")

    links = []

    for a in soup.select("a[href*='/voitures_d_occasion/']"):
        href = a.get("href")
        if href and "http" not in href:
            href = "https://www.avito.ma" + href
        links.append(href)

    return list(set(links))


# ---------------------------
# 2. SCRAPE ONE DETAIL PAGE
# ---------------------------
def scrape_car(url):
    r = requests.get(url, headers=HEADERS)
    soup = BeautifulSoup(r.text, "html.parser")

    def get_value(label):
        # cherche texte contenant le label
        tag = soup.find(text=lambda x: x and label.lower() in x.lower())
        if tag:
            parent = tag.find_parent()
            return parent.get_text(" ").strip()
        return None

    title = soup.find("h1")
    title = title.text.strip() if title else None

    price = soup.select_one("[data-testid='price']")
    price = price.text.strip() if price else None

    return {
        "title": title,
        "url": url,
        "price": price,
        "year": get_value("Année"),
        "mileage": get_value("Kilométrage"),
        "fuel": get_value("Carburant"),
        "gearbox": get_value("Boîte"),
        "brand": get_value("Marque"),
        "model": get_value("Modèle"),
        "scraped_at": datetime.utcnow().isoformat()
    }


# ---------------------------
# 3. PIPELINE COMPLETE
# ---------------------------
def run(list_url, limit=10):
    links = get_links(list_url)
    data = []

    for i, link in enumerate(links[:limit]):
        print(f"[{i}] scraping detail:", link)

        try:
            car = scrape_car(link)
            data.append(car)
            time.sleep(1)  # éviter blocage
        except Exception as e:
            print("error:", e)

    return data


# ---------------------------
# EXECUTION
# ---------------------------
if __name__ == "__main__":
    url = "https://www.avito.ma/fr/voitures_d_occasion"
    dataset = run(url, limit=20)

    print(dataset)