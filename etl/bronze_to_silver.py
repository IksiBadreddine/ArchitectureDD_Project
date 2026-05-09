"""
ETL: Bronze → Silver
Nettoyage et structuration des données scrapées
Exécution: uv run python etl/bronze_to_silver.py
"""

import pandas as pd
import numpy as np
from datetime import datetime
import os

print("="*70)
print("🔄 ETL: BRONZE → SILVER (Version personnalisée)")
print("📊 Détection des valeurs aberrantes avec IQR")
print("💾 Sauvegarde: Parquet + CSV")
print("="*70)

# ==================== CONFIGURATION ====================
INPUT_FILE = "data/bronze/espacevoiture_final_20260503_211549.csv"  
timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
OUTPUT_PARQUET = f"silver_voitures_{timestamp}.parquet"
OUTPUT_CSV = f"silver_voitures_{timestamp}.csv"
# =======================================================

# 1. CHARGEMENT
print(f"\n📥 Chargement du fichier: {INPUT_FILE}")
df = pd.read_csv(INPUT_FILE)
print(f"   → {len(df)} lignes chargées")

# 2. SUPPRESSION DES DOUBLONS
print("\n🔍 Suppression des doublons...")
initial_count = len(df)
df = df.drop_duplicates(subset=['url'], keep='first')
print(f"   → {initial_count - len(df)} doublons supprimés")
print(f"   → {len(df)} annonces uniques")

# 3. NETTOYAGE DES PRIX
print("\n💰 Nettoyage des prix...")
df['prix'] = pd.to_numeric(df['prix'], errors='coerce')
prix_valides = df['prix'].notna().sum()
print(f"   → {prix_valides} annonces avec prix valide")

# 4. DÉTECTION DES VALEURS ABERRANTES (Méthode IQR)
print("\n📊 Détection des valeurs aberrantes (méthode IQR)...")

def detect_outliers_iqr(data, column):
    """Détecte les outliers avec la méthode IQR (Intervalle Interquartile)"""
    Q1 = data[column].quantile(0.25)
    Q3 = data[column].quantile(0.75)
    IQR = Q3 - Q1
    lower_bound = Q1 - 1.5 * IQR
    upper_bound = Q3 + 1.5 * IQR
    outliers = data[(data[column] < lower_bound) | (data[column] > upper_bound)]
    return outliers, lower_bound, upper_bound

# Appliquer sur les prix
prix_outliers, prix_lower, prix_upper = detect_outliers_iqr(df[df['prix'].notna()], 'prix')
print(f"\n   Prix - Bornes: [{prix_lower:,.0f} DH - {prix_upper:,.0f} DH]")
print(f"   Prix - {len(prix_outliers)} valeurs aberrantes détectées")

# Appliquer sur le kilométrage
km_outliers, km_lower, km_upper = detect_outliers_iqr(df[df['kilometrage'].notna()], 'kilometrage')
print(f"\n   Kilométrage - Bornes: [{km_lower:,.0f} km - {km_upper:,.0f} km]")
print(f"   Kilométrage - {len(km_outliers)} valeurs aberrantes détectées")

# Suppression des outliers
initial_count = len(df)
df = df[
    (df['prix'].isna()) |  # Garder les prix manquants
    ((df['prix'] >= prix_lower) & (df['prix'] <= prix_upper))
]
df = df[
    (df['kilometrage'].isna()) |  # Garder les km manquants
    ((df['kilometrage'] >= km_lower) & (df['kilometrage'] <= km_upper))
]
print(f"\n   → {initial_count - len(df)} annonces avec valeurs aberrantes supprimées")
print(f"   → {len(df)} annonces restantes")

# 5. NETTOYAGE DES ANNÉES (bornes naturelles)
print("\n📅 Nettoyage des années...")
df['annee'] = pd.to_numeric(df['annee'], errors='coerce')
initial_count = len(df)
df = df[(df['annee'].isna()) | ((df['annee'] >= 1990) & (df['annee'] <= 2026))]
print(f"   → {initial_count - len(df)} annonces avec années invalides supprimées")

# 5.5 GESTION DES VALEURS MANQUANTES
print("\n🛠️ Gestion des valeurs manquantes...")

# Supprimer les lignes où l'année est manquante
initial_count = len(df)
df = df.dropna(subset=['annee'])
print(f"   → {initial_count - len(df)} lignes supprimées (année manquante)")

# Remplacer les kilométrages manquants par la moyenne
km_moyen = df['kilometrage'].mean()
km_manquants = df['kilometrage'].isna().sum()
df['kilometrage'] = df['kilometrage'].fillna(km_moyen)
print(f"   → {km_manquants} kilométrages manquants remplacés par la moyenne: {km_moyen:.0f} km")

# 6. AJOUT DE L'ÂGE DU VÉHICULE
current_year = datetime.now().year
df['age_vehicule'] = current_year - df['annee']
print(f"   → Âge moyen: {df['age_vehicule'].mean():.1f} ans")

# 7. STANDARDISATION DES VILLES (uniquement lower case)
print("\n🏙️ Standardisation des villes (lower case)...")
df['ville'] = df['ville'].str.lower().str.strip()
# Remplacer "casa" par "casablanca"
df.loc[df['ville'] == 'casa', 'ville'] = 'casablanca'
print(f"   → Villes uniques: {df['ville'].nunique()}")
print(f"   → Exemples: {df['ville'].dropna().unique()[:10].tolist()}")

# 8. MARQUES MANQUANTES - LAISSÉES VIDES (pas de traitement)
print("\n🏭 Marques manquantes...")
marques_manquantes = df['marque'].isna().sum()
print(f"   → {marques_manquantes} annonces sans marque (laissées vides)")

# 9. TRANCHES DE PRIX (si prix présent)
print("\n💰 Création des tranches de prix...")
def prix_tranche(prix):
    if pd.isna(prix):
        return 'Prix non disponible'
    elif prix < 50000:
        return 'Moins de 50k DH'
    elif prix < 100000:
        return '50k - 100k DH'
    elif prix < 150000:
        return '100k - 150k DH'
    elif prix < 200000:
        return '150k - 200k DH'
    else:
        return 'Plus de 200k DH'

df['tranche_prix'] = df['prix'].apply(prix_tranche)
print(f"   → Distribution: {df['tranche_prix'].value_counts().to_dict()}")

# 10. SÉLECTION DES COLONNES (URL en dernière position)
print("\n📋 Sélection des colonnes...")
columns_silver = [
    'titre', 'marque', 'modele', 'prix', 'annee', 'age_vehicule',
    'kilometrage', 'carburant', 'transmission', 'ville', 'date_annonce',
    'date_scraping', 'tranche_prix', 'url'
]

# Ne garder que les colonnes qui existent
existing_columns = [col for col in columns_silver if col in df.columns]
df_silver = df[existing_columns].copy()
print(f"   → Colonnes conservées: {existing_columns}")

# 11. SAUVEGARDE EN PARQUET + CSV
print(f"\n💾 Sauvegarde des données nettoyées...")

# Sauvegarde Parquet
df_silver.to_parquet(OUTPUT_PARQUET, index=False)
print(f"   ✅ Parquet: {OUTPUT_PARQUET}")
print(f"      Taille: {os.path.getsize(OUTPUT_PARQUET) / 1024:.1f} KB")

# Sauvegarde CSV (pour Excel/visualisation)
df_silver.to_csv(OUTPUT_CSV, index=False, encoding='utf-8-sig')
print(f"   ✅ CSV: {OUTPUT_CSV}")
print(f"      Taille: {os.path.getsize(OUTPUT_CSV) / 1024:.1f} KB")

print(f"\n   → {len(df_silver)} annonces nettoyées sauvegardées")

# 12. APERÇU
print("\n📊 APERÇU DES DONNÉES SILVER:")
print(df_silver.head(10).to_string())

# 13. STATISTIQUES FINALES
print("\n" + "="*70)
print("📈 STATISTIQUES FINALES (SILVER LAYER):")
print(f"   Nombre total d'annonces: {len(df_silver)}")
print(f"   Prix - Moyenne: {df_silver['prix'].mean():,.0f} DH")
print(f"   Prix - Médiane: {df_silver['prix'].median():,.0f} DH")
print(f"   Prix - Min: {df_silver['prix'].min():,.0f} DH")
print(f"   Prix - Max: {df_silver['prix'].max():,.0f} DH")
print(f"   Année moyenne: {df_silver['annee'].mean():.0f}")
print(f"   Âge moyen: {df_silver['age_vehicule'].mean():.1f} ans")
print(f"   Kilométrage moyen: {df_silver['kilometrage'].mean():,.0f} km")
print(f"   Marques: {df_silver['marque'].nunique()} uniques ({marques_manquantes} manquantes)")
print(f"   Villes: {df_silver['ville'].nunique()} uniques")
print("="*70)

print("\n✅ ÉTAPE 2 TERMINÉE: Bronze → Silver")
print(f"   📁 Fichiers créés:")
print(f"      - {OUTPUT_PARQUET} (format Big Data)")
print(f"      - {OUTPUT_CSV} (format Excel)")