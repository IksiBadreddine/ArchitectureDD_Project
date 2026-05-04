"""
Upload des données Bronze et Silver vers MinIO (Data Lake)
Exécution: uv run python data_lake/upload_to_minio.py
"""

import os
from minio import Minio
from minio.error import S3Error
from datetime import datetime
import glob

print("="*70)
print("📀 UPLOAD VERS DATA LAKE (MINIO)")
print("="*70)

# Connexion à MinIO
client = Minio(
    "localhost:9000",
    access_key="minioadmin",
    secret_key="minioadmin123",
    secure=False
)

# Buckets
BRONZE_BUCKET = "bronze-auto"
SILVER_BUCKET = "silver-auto"
GOLD_BUCKET = "gold-auto"

# Création des buckets s'ils n'existent pas
print("\n📁 Vérification des buckets...")
for bucket in [BRONZE_BUCKET, SILVER_BUCKET, GOLD_BUCKET]:
    if not client.bucket_exists(bucket):
        client.make_bucket(bucket)
        print(f"   ✅ Bucket créé: {bucket}")
    else:
        print(f"   📁 Bucket existe déjà: {bucket}")

# 1. Upload du fichier Bronze (CSV brut du scraper)
print("\n📤 Upload des données BRONZE...")

bronze_files = glob.glob("data/bronze/espacevoiture_final_20260503_211549.csv")
# Filtrer pour prendre le plus récent
if bronze_files:
    bronze_file = max(bronze_files, key=os.path.getctime)
    date_path = datetime.now().strftime("%Y/%m/%d")
    object_name = f"raw/{date_path}/bronze_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
    
    try:
        client.fput_object(BRONZE_BUCKET, object_name, bronze_file)
        print(f"   ✅ {bronze_file} → {BRONZE_BUCKET}/{object_name}")
        print(f"      Taille: {os.path.getsize(bronze_file) / 1024:.1f} KB")
    except S3Error as e:
        print(f"   ❌ Erreur: {e}")
else:
    print("   ⚠️ Aucun fichier Bronze trouvé (espacevoiture_*.csv)")

# 2. Upload du fichier Silver (Parquet nettoyé)
print("\n📤 Upload des données SILVER...")

silver_files = glob.glob("data/silver/silver_voitures_20260504_015638.parquet")

if silver_files:
    silver_file = max(silver_files, key=os.path.getctime)
    date_path = datetime.now().strftime("%Y/%m/%d")
    object_name = f"cleaned/{date_path}/silver_{datetime.now().strftime('%Y%m%d_%H%M%S')}.parquet"
    
    try:
        client.fput_object(SILVER_BUCKET, object_name, silver_file)
        print(f"   ✅ {silver_file} → {SILVER_BUCKET}/{object_name}")
        print(f"      Taille: {os.path.getsize(silver_file) / 1024:.1f} KB")
    except S3Error as e:
        print(f"   ❌ Erreur: {e}")
else:
    # Chercher aussi les CSV Silver
    silver_csv = glob.glob("data/silver/silver_voitures_20260504_015638.csv")
    if silver_csv:
        silver_file = max(silver_csv, key=os.path.getctime)
        date_path = datetime.now().strftime("%Y/%m/%d")
        object_name = f"cleaned/{date_path}/silver_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        
        try:
            client.fput_object(SILVER_BUCKET, object_name, silver_file)
            print(f"   ✅ {silver_file} → {SILVER_BUCKET}/{object_name}")
        except S3Error as e:
            print(f"   ❌ Erreur: {e}")
    else:
        print("   ⚠️ Aucun fichier Silver trouvé (silver_voitures_*.parquet ou .csv)")

print("\n" + "="*70)
print("✅ Données uploadées vers le Data Lake (MinIO)")
print("🌐 Console: http://localhost:9001")
print("="*70)

# Afficher le contenu des buckets
print("\n📊 CONTENU DES BUCKETS:")
for bucket in [BRONZE_BUCKET, SILVER_BUCKET]:
    print(f"\n   📁 {bucket}:")
    objects = client.list_objects(bucket, recursive=True)
    for obj in objects:
        print(f"      - {obj.object_name} ({obj.size // 1024} KB)")