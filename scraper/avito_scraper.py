import requests
from bs4 import BeautifulSoup
import json
import re
import time
from datetime import datetime
from urllib.parse import urljoin
from fake_useragent import UserAgent

BASE_URL = "https://www.avito.ma"
ua = UserAgent()


# =========================
# HEADERS ANTI-BOT
# =========================
def get_headers():
    return {
        "User-Agent": ua.random,
        "Accept-Language": "fr-FR,fr;q=0.9",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Connection": "keep-alive",
    }


# =========================
# DEBUG RESPONSE
# =========================
def debug(response):
    print("\n================ DEBUG ================")
    print("STATUS:", response.status_code)
    print("URL:", response.url)
    print("HTML SIZE:", len(response.text))
    print("======================================\n")


# =========================
# CLEAN PRICE (SAFE)
# =========================
def clean_price(text):
    if not text:
        return None

    numbers = re.findall(r"\d+", text.replace(" ", ""))
    if not numbers:
        return None

    try:
        value = int("".join(numbers))
        # filtre anti-bugs (prix absurdes)
        if value > 5_000_000:
            return None
        return value
    except:
        return None


# =========================
# EXTRACT YEAR
# =========================
def extract_year(text):
    match = re.search(r"(20\d{2})", text)
    if not match:
        return None

    year = int(match.group(1))
    if 1990 <= year <= 2026:
        return year
    return None


# =========================
# EXTRACT KM
# =========================
def extract_km(text):
    match = re.search(r"(\d[\d\s]{0,10})\s*km", text.lower())
    if match:
        try:
            km = int(match.group(1).replace(" ", ""))
            if km < 1_000_000:
                return km
        except:
            return None
    return None


# =========================
# PARSE ONE LISTING PAGE
# =========================
def parse_listing(url):
    try:
        r = requests.get(url, headers=get_headers(), timeout=10)
        if r.status_code != 200:
            return None

        soup = BeautifulSoup(r.text, "html.parser")

        # TITLE (robust)
        title = None
        h1 = soup.find("h1")
        if h1:
            title = h1.get_text(strip=True)

        # PRICE (multiple fallback selectors)
        price = None
        price_tag = soup.find(string=re.compile(r"\d+\s*dh", re.I))
        if price_tag:
            price = clean_price(price_tag)

        # fallback meta
        if not price:
            meta_price = soup.find("meta", property="product:price:amount")
            if meta_price:
                price = clean_price(meta_price.get("content"))

        # FULL TEXT CLEAN
        full_text = soup.get_text(" ", strip=True)

        data = {
            "title": title,
            "price": price,
            "year": extract_year(full_text),
            "mileage": extract_km(full_text),
            "url": url,
            "scraped_at": datetime.now().isoformat()
        }

        # validation (anti garbage)
        if not data["title"] and not data["price"]:
            return None

        return data

    except Exception as e:
        print("❌ listing error:", url, e)
        return None


# =========================
# SCRAPE SEARCH PAGE LINKS
# =========================
def get_links(search_url):
    r = requests.get(search_url, headers=get_headers())
    if r.status_code != 200:
        return []

    soup = BeautifulSoup(r.text, "html.parser")

    links = set()

    for a in soup.find_all("a", href=True):
        href = a["href"]

        # IMPORTANT: only car listings
        if "/voitures_d_occasion/" in href:
            full = urljoin(BASE_URL, href)
            links.add(full)

    return list(links)


# =========================
# MAIN SCRAPER
# =========================
def scrape_avito(base_url, pages=3, limit=50):
    results = []

    for page in range(1, pages + 1):

        url = f"{base_url}?o={page}"
        print(f"\n🔎 Page {page}: {url}")

        r = requests.get(url, headers=get_headers())
        debug(r)

        links = get_links(url)

        print(f"🔗 links found: {len(links)}")

        for link in links:
            if len(results) >= limit:
                break

            print("➡ scraping:", link)
            item = parse_listing(link)

            if item:
                results.append(item)

            time.sleep(1.2)

        time.sleep(2)

    return results


# =========================
# RUN
# =========================
if __name__ == "__main__":
    url = "https://www.avito.ma/fr/maroc/voitures_d_occasion"

    data = scrape_avito(url, pages=5, limit=50)

    print("\n✅ TOTAL:", len(data))

    # FORCE SAVE (fix ton problème fichier)
    with open("avito_clean.json", "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4, ensure_ascii=False)

    print("💾 saved: avito_clean.json")