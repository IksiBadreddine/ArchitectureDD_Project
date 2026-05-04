"""
Batch Ingestion - Scraping programmé toutes les heures
Stockage dans MinIO (Data Lake)
Exécution manuelle: uv run python ingestion/batch_ingestion.py
"""

import os
import sys
import pandas as pd
from datetime import datetime
from minio import Minio
import glob

# Ajouter le parent au path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from scraper.scraper_espacevoiture2 import EspaceVoitureScraper

print("="*70)
print("📦 BATCH INGESTION - Scraping programmé")
print(f"🕐 Date et heure: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
print("="*70)

# ==================== CONFIGURATION ====================
BATCH_ID = datetime.now().strftime("%Y%m%d_%H%M%S")
PAGES_TO_SCRAPE = 5   # 5 pages par batch (~100 annonces)
# =======================================================

# 1. Connexion à MinIO
print("\n📀 Connexion à MinIO...")
client = Minio(
    "localhost:9000",
    access_key="minioadmin",
    secret_key="minioadmin123",
    secure=False
)

BRONZE_BUCKET = "bronze-auto"

if not client.bucket_exists(BRONZE_BUCKET):
    client.make_bucket(BRONZE_BUCKET)
    print(f"   ✅ Bucket {BRONZE_BUCKET} créé")
else:
    print(f"   ✅ Bucket {BRONZE_BUCKET} existe")

# 2. Scraping
print(f"\n🚗 Scraping de {PAGES_TO_SCRAPE} pages...")
scraper = EspaceVoitureScraper()
annonces = scraper.scrape_all_pages(max_pages=PAGES_TO_SCRAPE, get_details=False)

print(f"\n   → {len(annonces)} annonces collectées")

# 3. Sauvegarde et upload
if annonces:
    df = pd.DataFrame(annonces)
    temp_file = f"batch_{BATCH_ID}.csv"
    df.to_csv(temp_file, index=False, encoding="utf-8-sig")
    
    # Upload vers MinIO
    date_path = datetime.now().strftime("%Y/%m/%d")
    object_name = f"batch/{date_path}/batch_{BATCH_ID}.csv"
    
    client.fput_object(BRONZE_BUCKET, object_name, temp_file)
    print(f"\n📤 Upload vers MinIO:")
    print(f"   ✅ {object_name}")
    print(f"   📊 {len(annonces)} annonces")
    
    # Nettoyage
    os.remove(temp_file)
    print(f"   🗑️ Fichier temporaire supprimé")

print("\n✅ Batch ingestion terminée")