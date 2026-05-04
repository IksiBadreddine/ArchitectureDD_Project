"""
Streaming Ingestion - Simulation d'annonces en temps réel
Exécution: uv run python ingestion/streaming_ingestion.py
"""

import json
import random
import time
import io
from datetime import datetime
from minio import Minio

print("="*70)
print("⚡ STREAMING INGESTION - Temps réel")
print("   Chaque nouvelle annonce = 1 événement")
print("   Appuyez sur Ctrl+C pour arrêter")
print("="*70)

# ==================== CONFIGURATION ====================
INTERVAL_SECONDS = 3   # 1 annonce toutes les 3 secondes
MAX_EVENTS = 20        # 20 événements pour la démo
# =======================================================

# Connexion à MinIO
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

# Données simulées
MARQUES = ['Dacia', 'Renault', 'Peugeot', 'Volkswagen', 'BMW', 'Mercedes', 'Audi']
MODELES = {
    'Dacia': ['Logan', 'Sandero', 'Duster'],
    'Renault': ['Clio', 'Megane', 'Captur'],
    'Peugeot': ['208', '308', '2008'],
    'Volkswagen': ['Golf', 'Polo', 'Tiguan'],
    'BMW': ['Serie 1', 'Serie 3', 'X1'],
    'Mercedes': ['Classe A', 'Classe C', 'GLA'],
    'Audi': ['A3', 'A4', 'Q3']
}
VILLES = ['Casablanca', 'Rabat', 'Tanger', 'Marrakech', 'Fès']
CARBURANTS = ['Diesel', 'Essence']
TRANSMISSIONS = ['Manuelle', 'Automatique']

def generate_annonce(event_id):
    marque = random.choice(MARQUES)
    modele = random.choice(MODELES[marque])
    return {
        'event_id': event_id,
        'timestamp': datetime.now().isoformat(),
        'type': 'nouvelle_annonce',
        'data': {
            'titre': f"{marque} {modele}",
            'marque': marque,
            'modele': modele,
            'prix': random.randint(50000, 500000),
            'annee': random.randint(2018, 2025),
            'kilometrage': random.randint(10000, 150000),
            'carburant': random.choice(CARBURANTS),
            'transmission': random.choice(TRANSMISSIONS),
            'ville': random.choice(VILLES),
            'url': f"https://espacevoiture.com/stream_{event_id}"
        }
    }

print(f"\n⚡ Démarrage du streaming...")
print(f"   ⏱️ 1 annonce toutes les {INTERVAL_SECONDS} secondes")
print(f"   🎯 {MAX_EVENTS} événements\n")

try:
    for event_id in range(1, MAX_EVENTS + 1):
        annonce = generate_annonce(event_id)
        prix = annonce['data']['prix']
        titre = annonce['data']['titre']
        
        # Convertir en JSON
        json_data = json.dumps(annonce, ensure_ascii=False, indent=2)
        
        # Créer un objet fichier en mémoire (BytesIO)
        data = io.BytesIO(json_data.encode('utf-8'))
        
        # Stockage dans MinIO
        date_path = datetime.now().strftime("%Y/%m/%d")
        object_name = f"streaming/{date_path}/event_{event_id}_{datetime.now().strftime('%H%M%S')}.json"
        
        client.put_object(
            BRONZE_BUCKET, 
            object_name, 
            data, 
            length=len(json_data),
            content_type='application/json'
        )
        
        print(f"📨 [{event_id:2d}/{MAX_EVENTS}] {titre:20} - {prix:>8,} DH → {object_name}")
        
        if event_id < MAX_EVENTS:
            time.sleep(INTERVAL_SECONDS)
            
except KeyboardInterrupt:
    print("\n\n🛑 Streaming arrêté par l'utilisateur")

print("\n✅ Streaming ingestion terminée")