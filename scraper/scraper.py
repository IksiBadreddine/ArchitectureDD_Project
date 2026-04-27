"""
Scraper Avito.ma corrigé - Extrait uniquement les annonces individuelles
Exécution: uv run python scraper_avito_corrected.py
"""

import time
import random
import pandas as pd
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import re
from datetime import datetime

print("="*60)
print("🚗 SCRAPER AVITO.MA - ANNONCES AUTOMOBILE")
print("="*60)

# =========================
# CONFIGURATION
# =========================
def setup_driver():
    chrome_options = Options()
    chrome_options.add_argument("--headless=new")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-blink-features=AutomationControlled")
    chrome_options.add_argument("--window-size=1920,1080")
    chrome_options.add_argument("--lang=fr-FR")
    chrome_options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
    chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
    chrome_options.add_experimental_option('useAutomationExtension', False)
    
    driver = webdriver.Chrome(
        service=Service(ChromeDriverManager().install()),
        options=chrome_options
    )
    driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
    print("✅ Navigateur configuré")
    return driver

def extract_price(text):
    """Extrait le prix du texte"""
    patterns = [
        r'(\d[\d\s]*\d?)\s*(?:DH|DA)',
        r'(\d{1,3}(?:[\s,]\d{3})*)\s*DH'
    ]
    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            price_str = match.group(1).replace(' ', '').replace(',', '')
            try:
                return int(price_str)
            except:
                pass
    return None

def extract_kilometers(text):
    """Extrait le kilométrage"""
    match = re.search(r'(\d[\d\s]*\d?)\s*(?:KM|Km|kilomètres?)', text, re.IGNORECASE)
    if match:
        km_str = match.group(1).replace(' ', '').replace(',', '')
        try:
            return int(km_str)
        except:
            pass
    return None

def extract_year(text):
    """Extrait l'année"""
    match = re.search(r'\b(19|20)\d{2}\b', text)
    if match:
        return int(match.group(0))
    return None

def extract_marque(title):
    """Détecte la marque"""
    marques = {
        'Dacia': ['dacia', 'logan', 'sandero', 'duster'],
        'Renault': ['renault', 'clio', 'megane', 'captur'],
        'Peugeot': ['peugeot', '208', '308', '508'],
        'Citroën': ['citroen', 'c3', 'c4'],
        'Volkswagen': ['volkswagen', 'golf', 'polo', 'tiguan'],
        'BMW': ['bmw', 'serie'],
        'Mercedes': ['mercedes', 'classe'],
        'Audi': ['audi', 'a3', 'a4'],
        'Toyota': ['toyota', 'yaris', 'corolla'],
        'Hyundai': ['hyundai', 'i10', 'i20'],
        'Kia': ['kia'],
        'Ford': ['ford']
    }
    title_lower = title.lower()
    for marque, keywords in marques.items():
        for keyword in keywords:
            if keyword in title_lower:
                return marque
    return "Autre"

def is_valid_car_url(url):
    """Vérifie si l'URL pointe vers une annonce de voiture individuelle"""
    # Exclure les pages de catégorie
    invalid_patterns = [
        'voitures-à_vendre',
        'voitures-occasion',
        'véhicules_autres',
        'motos',
        'velos',
        'camions',
        'bateaux',
        '?o=',
        '?p='
    ]
    
    for pattern in invalid_patterns:
        if pattern in url:
            return False
    
    # Doit contenir 'annonce' et idéalement un ID numérique
    if 'annonce' in url and ('/' in url.count('/') >= 5):
        return True
    
    return False

def get_car_details(driver, url):
    """Extrait les détails d'une annonce individuelle"""
    try:
        driver.get(url)
        time.sleep(random.uniform(2, 4))
        
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.TAG_NAME, "body"))
        )
        
        soup = BeautifulSoup(driver.page_source, "html.parser")
        
        # Titre - chercher h1
        title_tag = soup.find("h1")
        if not title_tag:
            title_tag = soup.find("h2", class_=re.compile(r'title', re.I))
        
        titre = title_tag.text.strip() if title_tag else "N/A"
        
        # Texte complet
        full_text = soup.get_text()
        
        # Extraction des données
        data = {
            "url": url,
            "titre": titre,
            "prix": extract_price(full_text),
            "kilometrage": extract_kilometers(full_text),
            "annee": extract_year(full_text),
            "marque": extract_marque(titre),
            "date_scraping": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
        
        # Vérifier que c'est une voiture (et pas autre chose)
        if any(word in titre.lower() for word in ['moto', 'velo', 'bateau', 'camion']):
            data["categorie"] = "autre"
        else:
            data["categorie"] = "voiture"
        
        return data
        
    except Exception as e:
        print(f"   ❌ Erreur: {e}")
        return None

def scrape_annonces(max_ads=30):
    """Scrape les annonces depuis Avito"""
    base_url = "https://www.avito.ma/fr/maroc/voitures"
    page = 1
    all_data = []
    seen_urls = set()
    
    print(f"\n🎯 Objectif: {max_ads} annonces de voitures\n")
    
    while len(all_data) < max_ads and page <= 5:
        url = f"{base_url}?o={page}" if page > 1 else base_url
        print(f"\n📄 Page {page}: {url}")
        
        try:
            driver.get(url)
            time.sleep(random.uniform(3, 5))
            
            soup = BeautifulSoup(driver.page_source, "html.parser")
            
            # Chercher les liens d'annonces individuelles
            urls = []
            
            # Méthode: chercher les liens qui contiennent /annonce/ et un ID
            for a in soup.find_all("a", href=True):
                href = a['href']
                
                # Construire URL complète
                if href.startswith('/'):
                    full_url = "https://www.avito.ma" + href
                else:
                    full_url = href
                
                # Filtrer les URLs valides
                if 'annonce' in full_url and is_valid_car_url(full_url):
                    # Nettoyer l'URL (enlever les paramètres)
                    clean_url = full_url.split('?')[0]
                    if clean_url not in seen_urls:
                        seen_urls.add(clean_url)
                        urls.append(clean_url)
            
            # Supprimer les doublons
            urls = list(set(urls))
            print(f"   → {len(urls)} annonces individuelles trouvées")
            
            if not urls:
                print("   ⚠️ Aucune annonce trouvée, vérification du HTML...")
                # Afficher un exemple de lien trouvé
                sample_links = [a['href'] for a in soup.find_all("a", href=True) if '/annonce/' in a['href']][:3]
                print(f"   Exemples de liens trouvés: {sample_links}")
            
            for i, annonce_url in enumerate(urls):
                if len(all_data) >= max_ads:
                    break
                
                print(f"   [{i+1}/{len(urls)}] {annonce_url.split('/')[-2] if annonce_url.endswith('/') else annonce_url[-30:]}")
                
                data = get_car_details(driver, annonce_url)
                
                if data and data.get('prix') and data.get('categorie') == 'voiture':
                    all_data.append(data)
                    print(f"      ✅ {data['titre'][:45]} - {data['prix']:,} DH")
                elif data:
                    print(f"      ⏭️ Ignoré (catégorie: {data.get('categorie', 'inconnue')})")
                else:
                    print(f"      ❌ Échec extraction")
                
                # Pause pour éviter le blocage
                time.sleep(random.uniform(1.5, 3))
            
            page += 1
            
        except Exception as e:
            print(f"   ❌ Erreur page {page}: {e}")
            page += 1
            continue
    
    return all_data

# =========================
# MAIN
# =========================
if __name__ == "__main__":
    driver = setup_driver()
    
    try:
        annonces = scrape_annonces(max_ads=5)  # Commencer avec 15 pour test
        
        if annonces:
            df = pd.DataFrame(annonces)
            
            # Sauvegarde
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"avito_voitures_{timestamp}.csv"
            df.to_csv(filename, index=False, encoding="utf-8-sig")
            
            print("\n" + "="*60)
            print(f"✅ SUCCÈS! {len(df)} annonces sauvegardées")
            print(f"📁 Fichier: {filename}")
            
            print("\n📊 APERÇU DES DONNÉES:")
            print(df[['titre', 'prix', 'annee', 'kilometrage', 'marque']].head())
            
            if 'prix' in df.columns:
                prix_valides = df[df['prix'].notna()]['prix']
                if len(prix_valides) > 0:
                    print(f"\n💰 STATISTIQUES DES PRIX:")
                    print(f"   Nombre: {len(prix_valides)} annonces")
                    print(f"   Moyenne: {prix_valides.mean():,.0f} DH")
                    print(f"   Médiane: {prix_valides.median():,.0f} DH")
                    print(f"   Min: {prix_valides.min():,.0f} DH")
                    print(f"   Max: {prix_valides.max():,.0f} DH")
            
            if 'marque' in df.columns:
                print(f"\n🏆 TOP MARQUES:")
                marques = df[df['marque'] != 'Autre']['marque'].value_counts()
                for marque, count in marques.head(5).items():
                    print(f"   {marque}: {count} annonces")
            
        else:
            print("\n❌ Aucune annonce extraite")
            print("\n💡 SUGGESTIONS:")
            print("   1. Avito bloque peut-être le scraping")
            print("   2. Essayez avec Moteur.ma comme alternative")
            
    finally:
        driver.quit()
    
    print("\n🏁 Scraping terminé")