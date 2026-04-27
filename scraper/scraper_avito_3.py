import time
import pandas as pd
from bs4 import BeautifulSoup

from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager

from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC


# =========================
# CONFIG CHROME
# =========================
chrome_options = Options()

# ⚠️ headless amélioré (moins détectable)
chrome_options.add_argument("--headless=new")
chrome_options.add_argument("--disable-gpu")
chrome_options.add_argument("--no-sandbox")
chrome_options.add_argument("--disable-dev-shm-usage")
chrome_options.add_argument("--disable-blink-features=AutomationControlled")
chrome_options.add_argument("user-agent=Mozilla/5.0")

driver = webdriver.Chrome(
    service=Service(ChromeDriverManager().install()),
    options=chrome_options
)


# =========================
# EXTRACTION DÉTAIL ANNONCE
# =========================
def get_car_details(url):
    try:
        driver.get(url)

        # attente dynamique (IMPORTANT)
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.TAG_NAME, "h1"))
        )

        soup = BeautifulSoup(driver.page_source, "html.parser")

        data = {
            "lien": url,
            "titre": soup.find("h1").text.strip() if soup.find("h1") else None,
        }

        # prix (sélecteur fragile → fallback)
        price_tag = soup.find("span") or soup.find("div")
        data["prix"] = price_tag.text.strip() if price_tag else None

        # extraction infos générales (robuste)
        spans = soup.find_all("span")
        clean_info = [s.text.strip() for s in spans if s.text.strip()]

        data["raw_info"] = clean_info

        return data

    except Exception as e:
        print(f"❌ erreur {url} : {e}")
        return None


# =========================
# SCRAPER LISTING
# =========================
def scrape_annonces(max_ads=50):
    base_url = "https://www.avito.ma/fr/maroc/voitures-%C3%A0_vendre"
    page = 1

    all_data = []

    while len(all_data) < max_ads:
        print(f"📄 Page {page}")

        driver.get(f"{base_url}?o={page}")

        time.sleep(3)  # laisse JS charger

        soup = BeautifulSoup(driver.page_source, "html.parser")

        # ✅ selector plus stable que classes CSS
        links = soup.select("a[href*='/fr/maroc']")

        urls = []
        for a in links:
            href = a.get("href")
            if href:
                full_url = "https://www.avito.ma" + href if href.startswith("/") else href
                urls.append(full_url)

        # supprimer doublons
        urls = list(set(urls))

        for url in urls:
            if len(all_data) >= max_ads:
                break

            print("🚗", url)

            data = get_car_details(url)

            if data:
                all_data.append(data)

            time.sleep(1.5)

        page += 1

    return all_data


# =========================
# RUN
# =========================
cars = scrape_annonces(max_ads=50)

df = pd.DataFrame(cars)

df.to_csv("avito_clean.csv", index=False, encoding="utf-8-sig")

driver.quit()

print("✅ terminé")