"""
ETL: Silver → Gold
Charge les données nettoyées vers le Data Warehouse (PostgreSQL)
Exécution: uv run python etl/silver_to_gold.py
"""

import pandas as pd
import psycopg2
from psycopg2.extras import execute_values
from datetime import datetime
import os
import glob

print("="*70)
print("🔄 ETL: SILVER → GOLD (Data Warehouse)")
print("="*70)

# ==================== CONFIGURATION ====================
# Connexion au Data Warehouse
DW_CONN = {
    'host': 'postgres-dw',  # ← Nom du service dans docker-compose (pas localhost!)
    'port': 5432,
    'database': 'gold_auto_market',
    'user': 'gold_user',
    'password': 'gold_password'
}

# Fichier Silver le plus récent
silver_files = glob.glob("data/silver/silver_voitures_20260504_015638.parquet")
if not silver_files:
    silver_files = glob.glob("data/silver/silver_voitures_20260504_015638.csv")

if not silver_files:
    print("❌ Aucun fichier Silver trouvé!")
    exit(1)

silver_file = max(silver_files, key=os.path.getctime)
print(f"\n📥 Chargement du fichier Silver: {silver_file}")

# Lecture du fichier Silver
if silver_file.endswith('.parquet'):
    df = pd.read_parquet(silver_file)
else:
    df = pd.read_csv(silver_file)

print(f"   → {len(df)} annonces chargées")
print(f"   → Colonnes: {df.columns.tolist()}")

# ==================== MAPPING DES MARQUES ====================
marque_mapping = {
    'Dacia': 'DACIA', 'Renault': 'RENAULT', 'Peugeot': 'PEUGEOT',
    'Citroën': 'CITROEN', 'Volkswagen': 'VOLKSWAGEN', 'BMW': 'BMW',
    'Mercedes': 'MERCEDES', 'Audi': 'AUDI', 'Toyota': 'TOYOTA',
    'Hyundai': 'HYUNDAI', 'Kia': 'KIA', 'Ford': 'FORD',
    'Opel': 'OPEL', 'Volvo': 'VOLVO'
}

# ==================== CONNEXION POSTGRESQL ====================
print("\n📀 Connexion au Data Warehouse...")
conn = psycopg2.connect(**DW_CONN)
cursor = conn.cursor()

# ==================== 1. CHARGEMENT DIMENSION MARQUES ====================
print("\n🏭 Chargement dimension marques...")
for marque_name, marque_code in marque_mapping.items():
    cursor.execute("""
        INSERT INTO dim_marque (code_marque, nom_marque) 
        VALUES (%s, %s)
        ON CONFLICT (code_marque) DO NOTHING
    """, (marque_code, marque_name))
conn.commit()
print(f"   → {len(marque_mapping)} marques insérées")

# ==================== 2. CHARGEMENT DIMENSION VILLES ====================
print("\n🏙️ Chargement dimension villes...")
villes = df['ville'].dropna().unique()
for ville in villes:
    cursor.execute("""
        INSERT INTO dim_ville (nom_ville) 
        VALUES (%s)
        ON CONFLICT (nom_ville) DO NOTHING
    """, (ville,))
conn.commit()
print(f"   → {len(villes)} villes insérées")

# ==================== 3. CHARGEMENT DIMENSION TEMPS ====================
print("\n📅 Chargement dimension temps...")
dates = df['date_annonce'].dropna().unique()
for date_str in dates:
    try:
        date_obj = datetime.strptime(date_str, '%d/%m/%Y')
        cursor.execute("""
            INSERT INTO dim_temps (date_annonce, annee, mois, trimestre)
            VALUES (%s, %s, %s, %s)
            ON CONFLICT (date_annonce) DO NOTHING
        """, (date_obj, date_obj.year, date_obj.month, (date_obj.month-1)//3 + 1))
    except:
        pass
conn.commit()
print(f"   → Dates traitées")

# ==================== 4. CHARGEMENT TABLE FAITS ====================
print("\n📊 Chargement table faits (annonces)...")

# Nettoyer les marques non mappées
df['marque_code'] = df['marque'].map(marque_mapping).fillna('AUTRE')

# Récupérer les IDs des dimensions
cursor.execute("SELECT id_marque, code_marque FROM dim_marque")
marque_ids = {code: id for id, code in cursor.fetchall()}

cursor.execute("SELECT id_ville, nom_ville FROM dim_ville")
ville_ids = {nom: id for id, nom in cursor.fetchall()}

# Préparer les données pour insertion
insert_count = 0
for _, row in df.iterrows():
    # Récupérer les IDs
    marque_id = marque_ids.get(row['marque_code'], 1)
    ville_id = ville_ids.get(row.get('ville'), None)
    
    # Récupérer l'ID temps
    date_annonce = None
    temps_id = None
    if pd.notna(row.get('date_annonce')):
        try:
            date_obj = datetime.strptime(row['date_annonce'], '%d/%m/%Y')
            cursor.execute("SELECT id_temps FROM dim_temps WHERE date_annonce = %s", (date_obj,))
            result = cursor.fetchone()
            if result:
                temps_id = result[0]
        except:
            pass
    
    # Insertion
    cursor.execute("""
        INSERT INTO fait_annonces (
            id_marque, id_ville, id_temps, source, prix, 
            kilometrage, annee_vehicule, age_vehicule, 
            carburant, transmission, nb_options, url
        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
    """, (
        marque_id, ville_id, temps_id, row.get('source'),
        row.get('prix'), row.get('kilometrage'), row.get('annee'),
        row.get('age_vehicule'), row.get('carburant'), 
        row.get('transmission'), row.get('nb_options', 0),
        row.get('url')
    ))
    insert_count += 1
    
    if insert_count % 500 == 0:
        conn.commit()
        print(f"   → {insert_count} annonces insérées...")

conn.commit()
print(f"   → {insert_count} annonces insérées au total")

# ==================== 5. AFFICHER LES ANALYSES ====================
print("\n" + "="*70)
print("📊 ANALYSES DEPUIS LE DATA WAREHOUSE")
print("="*70)

cursor.execute("SELECT * FROM v_prix_moyen_marque")
results = cursor.fetchall()
print("\n💰 PRIX MOYEN PAR MARQUE:")
for row in results[:10]:
    print(f"   {row[0]}: {row[1]} annonces - {row[2]:,.0f} DH")

cursor.execute("SELECT * FROM v_top_villes")
results = cursor.fetchall()
print("\n📍 TOP VILLES:")
for row in results:
    print(f"   {row[0]}: {row[1]} annonces - {row[2]:,.0f} DH")

cursor.execute("SELECT * FROM v_repartition_carburant")
results = cursor.fetchall()
print("\n⛽ RÉPARTITION PAR CARBURANT:")
for row in results:
    print(f"   {row[0]}: {row[1]} annonces - Prix moyen: {row[2]:,.0f} DH")

# ==================== FERMETURE ====================
cursor.close()
conn.close()

print("\n" + "="*70)
print("✅ ETL Silver → Gold terminé avec succès!")
print("📁 Data Warehouse accessible sur postgres://localhost:5433")
print("="*70)