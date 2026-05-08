"""
ETL: Bronze → Silver
Prend le dernier fichier Bronze, le nettoie et le fusionne avec le Silver existant
Exécution: uv run python etl/bronze_to_silver_v2.py
"""

import pandas as pd
import numpy as np
import os
import glob
from datetime import datetime
import re

print("="*70)
print("🔄 ETL: BRONZE → SILVER")
print("📊 Nettoyage des nouvelles annonces + fusion avec l'existant")
print("="*70)

# ==================== 1. CHARGEMENT DERNIER FICHIER BRONZE ====================
print("\n📥 Recherche du dernier fichier Bronze (batch)...")

bronze_files = glob.glob("batch_*.csv")
bronze_files.sort(key=os.path.getctime, reverse=True)

if not bronze_files:
    print("⚠️ Aucun fichier Bronze trouvé, recherche d'autres fichiers...")
    bronze_files = glob.glob("espacevoiture_*.csv")
    bronze_files.sort(key=os.path.getctime, reverse=True)

if not bronze_files:
    print("❌ Aucun fichier Bronze trouvé!")
    exit(1)

bronze_file = bronze_files[0]
print(f"   ✅ Fichier Bronze: {bronze_file} ({os.path.getsize(bronze_file) / 1024:.1f} KB)")

df_bronze = pd.read_csv(bronze_file)
print(f"   → {len(df_bronze)} nouvelles annonces brutes")

# ==================== 2. CHARGEMENT SILVER EXISTANT ====================
print("\n📥 Chargement du Silver existant...")

silver_files = glob.glob("silver_voitures_*.parquet")
silver_files.extend(glob.glob("data/silver/*.parquet"))
silver_files = [f for f in silver_files if os.path.exists(f)]

df_silver = pd.DataFrame()
if silver_files:
    silver_file = max(silver_files, key=os.path.getctime)
    print(f"   ✅ Fichier Silver existant: {silver_file}")
    df_silver = pd.read_parquet(silver_file)
    print(f"   → {len(df_silver)} annonces existantes")
else:
    print("   ℹ️ Aucun Silver existant, création d'un nouveau")

# ==================== 3. NETTOYAGE DES NOUVELLES ANNONCES ====================
print("\n🧹 Nettoyage des nouvelles annonces...")

# Nettoyer les prix
df_bronze['prix'] = pd.to_numeric(df_bronze.get('prix'), errors='coerce')

# Nettoyer les kilométrages
if 'kilometrage' in df_bronze.columns:
    df_bronze['kilometrage'] = df_bronze['kilometrage'].astype(str).str.replace(r'[^\d]', '', regex=True)
    df_bronze['kilometrage'] = pd.to_numeric(df_bronze['kilometrage'], errors='coerce')

# Année
if 'annee' in df_bronze.columns:
    df_bronze['annee'] = pd.to_numeric(df_bronze['annee'], errors='coerce')

# Supprimer les doublons d'URL
if 'url' in df_bronze.columns:
    df_bronze = df_bronze.drop_duplicates(subset=['url'], keep='first')

# Nettoyer les villes
if 'ville' in df_bronze.columns:
    df_bronze['ville'] = df_bronze['ville'].astype(str).str.lower().str.strip()
    df_bronze.loc[df_bronze['ville'] == 'casa', 'ville'] = 'casablanca'

# Ajouter l'âge du véhicule
current_year = datetime.now().year
df_bronze['age_vehicule'] = current_year - df_bronze['annee']

print(f"   → {len(df_bronze)} annonces après nettoyage")

# ==================== 4. FUSION AVEC SILVER EXISTANT ====================
print("\n🔀 Fusion avec les données existantes...")

if not df_silver.empty:
    # Garder toutes les colonnes communes
    common_cols = list(set(df_silver.columns) & set(df_bronze.columns))
    
    # Fusionner (éviter les doublons d'URL)
    df_combined = pd.concat([df_silver, df_bronze], ignore_index=True)
    
    if 'url' in df_combined.columns:
        df_combined = df_combined.drop_duplicates(subset=['url'], keep='last')
    
    print(f"   → Silver existant: {len(df_silver)}")
    print(f"   → Nouvelles annonces: {len(df_bronze)}")
    print(f"   → Total après fusion: {len(df_combined)}")
else:
    df_combined = df_bronze
    print(f"   → Nouveau Silver créé avec {len(df_combined)} annonces")

# ==================== 5. SAUVEGARDE ====================
print("\n💾 Sauvegarde du nouveau Silver...")

# Créer le dossier data/silver si nécessaire
os.makedirs("data/silver", exist_ok=True)

timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
output_file = f"data/silver/silver_voitures_{timestamp}.parquet"
df_combined.to_parquet(output_file, index=False)

print(f"   ✅ Fichier sauvegardé: {output_file}")
print(f"   📊 {len(df_combined)} annonces dans le Silver")
print(f"   📦 Taille: {os.path.getsize(output_file) / 1024:.1f} KB")

# Garder une copie dans le dossier courant
current_file = f"silver_voitures_{timestamp}.parquet"
df_combined.to_parquet(current_file, index=False)
print(f"   ✅ Copie: {current_file}")

# Supprimer le fichier Bronze temporaire
os.remove(bronze_file)
print(f"   🗑️ Fichier Bronze supprimé: {bronze_file}")

print("\n" + "="*70)
print("✅ ETL Bronze → Silver terminé avec succès!")
print("="*70)