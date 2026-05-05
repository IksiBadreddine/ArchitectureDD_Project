"""
Batch Ingestion - Version pour Docker
Scraping programmé et upload vers MinIO
"""

import os
import sys
import pandas as pd
import requests
from bs4 import BeautifulSoup
import re
import time
import random
from datetime import datetime
from minio import Minio
from urllib.parse import urljoin

print("="*70)
print("📦 BATCH INGESTION - Version Docker")
print(f"🕐 Date et heure: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
print("="*70)

# ==================== SCRAPER ====================
class EspaceVoitureScraper:
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9',
        })
        self.base_url = "https://www.espacevoiture.com"
    
    def clean_price(self, text):
        if not text:
            return None
        match = re.search(r'(\d[\d\s]*\d?)', text)
        return int(match.group(1).replace(' ', '')) if match else None
    
    def scrape_listing_page(self, page_num=1):
        url = self.base_url + "/voitures.html" if page_num == 1 else self.base_url + f"/voitures/page{page_num}.html"
        print(f"📄 Page {page_num}")
        
        try:
            response = self.session.get(url, timeout=15)
            if response.status_code != 200:
                return []
            
            soup = BeautifulSoup(response.content, 'html.parser')
            rows = soup.select('#resultContainer tr')
            
            annonces_page = []
            for row in rows:
                prix_elem = row.select_one('.prix')
                if not prix_elem:
                    continue
                
                modele_elem = row.select_one('p.descriptif a')
                if modele_elem:
                    titre = modele_elem.get_text(strip=True)
                    prix = self.clean_price(prix_elem.get_text(strip=True))
                    
                    if prix:
                        annonces_page.append({
                            'titre': titre, 'prix': prix,
                            'url': urljoin(self.base_url, modele_elem.get('href')),
                            'source': 'espacevoiture.com',
                            'date_scraping': datetime.now().isoformat()
                        })
                        print(f"   ✅ {titre[:35]} - {prix:,} DH")
            
            return annonces_page
        except Exception as e:
            print(f"❌ Erreur: {e}")
            return []
    
    def scrape_all_pages(self, max_pages=5):
        toutes = []
        for page in range(1, max_pages + 1):
            annonces = self.scrape_listing_page(page)
            toutes.extend(annonces)
            if page < max_pages and annonces:
                time.sleep(random.uniform(1, 2))
        return toutes

# ==================== MAIN ====================
BATCH_ID = datetime.now().strftime("%Y%m%d_%H%M%S")
PAGES_TO_SCRAPE = 5

# Connexion à MinIO (via Docker)
client = Minio(
    "minio:9000",  # Nom du service Docker
    access_key="minioadmin",
    secret_key="minioadmin123",
    secure=False
)

BRONZE_BUCKET = "bronze-auto"
if not client.bucket_exists(BRONZE_BUCKET):
    client.make_bucket(BRONZE_BUCKET)
    print(f"✅ Bucket {BRONZE_BUCKET} créé")

print(f"\n🚗 Scraping de {PAGES_TO_SCRAPE} pages...")
scraper = EspaceVoitureScraper()
annonces = scraper.scrape_all_pages(max_pages=PAGES_TO_SCRAPE)

if annonces:
    df = pd.DataFrame(annonces)
    temp_file = f"batch_{BATCH_ID}.csv"
    df.to_csv(temp_file, index=False, encoding="utf-8-sig")
    
    date_path = datetime.now().strftime("%Y/%m/%d")
    object_name = f"batch/{date_path}/batch_{BATCH_ID}.csv"
    
    client.fput_object(BRONZE_BUCKET, object_name, temp_file)
    print(f"\n📤 Upload: {object_name} ({len(annonces)} annonces)")
    os.remove(temp_file)

print("\n✅ Batch ingestion terminée")