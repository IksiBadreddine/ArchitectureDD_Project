"""
Scraper Avito.ma avec Selenium - Version corrigée
Filtre uniquement les URLs d'annonces de voitures
Exécution: uv run python scraper_avito_selenium_corrected.py
"""

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
import re

print("="*70)
print("🚗 SCRAPER AVITO.MA AVEC SELENIUM - VERSION CORRIGÉE")
print("="*70)

# =========================
# CONFIG CHROME
# =========================
chrome_options = Options()

# Options anti-détection
chrome_options.add_argument("--headless=new")
chrome_options.add_argument("--disable-gpu")
chrome_options.add_argument("--no-sandbox")
chrome_options.add_argument("--disable-dev-shm-usage")
chrome_options.add_argument("--disable-blink-features=AutomationControlled")
chrome_options.add_argument("--window-size=1920,1080")
chrome_options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
chrome_options.add_experimental_option('useAutomationExtension', False)

driver = webdriver.Chrome(
    service=Service(ChromeDriverManager().install()),
    options=chrome_options
)

driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")

# =========================
# FONCTIONS D'EXTRACTION
# =========================

def is_valid_car_url(url):
    """Vérifie si l'URL pointe vers une annonce de voiture"""
    # Exclure les pages de catégorie
    invalid_patterns = [
        'véhicules_autres',
        'voitures-à_vendre', 
        'motos',
        'vélos',
        'camions',
        'bateaux',
        '?o=',
        'annonces',
        'recherche'
    ]
    
    for pattern in invalid_patterns:
        if pattern in url:
            return False
    
    # Doit contenir une structure d'annonce valide
    # Exemple: /fr/maroc/voitures/annonce/123456789/...
    if '/voitures/annonce/' in url or '/fr/maroc/annonce/' in url:
        return True
    
    return False

def extract_price_from_text(text):
    """Extrait le prix du texte"""
    match = re.search(r'(\d[\d\s,]*\d?)\s*(?:DH|DA)', text, re.IGNORECASE)
    if match:
        price_str = match.group(1).replace(' ', '').replace(',', '')
        try:
            return int(price_str)
        except:
            pass
    return None

def get_car_details(url):
    """Récupère les détails d'une annonce de voiture"""
    try:
        driver.get(url)
        
        # Attendre le chargement
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.TAG_NAME, "h1"))
        )
        
        time.sleep(2)
        
        soup = BeautifulSoup(driver.page_source, "html.parser")
        
        # Titre
        title_tag = soup.find("h1")
        titre = title_tag.text.strip() if title_tag else None
        
        # Prix - chercher spécifiquement
        prix = None
        
        # Méthode 1: span avec classe spécifique
        price_spans = soup.find_all('span', class_=re.compile(r'PuYkS|price'))
        for span in price_spans:
            prix = extract_price_from_text(span.text)
            if prix:
                break
        
        # Méthode 2: chercher dans le texte
        if not prix:
            for text in soup.stripped_strings:
                prix = extract_price_from_text(text)
                if prix:
                    break
        
        # Extraction des caractéristiques
        annee = None
        kilometrage = None
        transmission = None
        carburant = None
        
        # Chercher dans les spans avec title
        for span in soup.find_all('span', title=True):
            title = span.get('title', '')
            text = span.text.strip()
            
            if 'Année' in title or 'Modele' in title:
                annee = text
            elif 'Kilométrage' in title:
                kilometrage = re.sub(r'[^\d]', '', text)
            elif 'Boite' in title:
                transmission = text
            elif 'Carburant' in title:
                carburant = text
        
        data = {
            "lien": url,
            "titre": titre,
            "prix": prix,
            "annee": annee,
            "kilometrage": kilometrage,
            "transmission": transmission,
            "carburant": carburant,
            "date_scraping": time.strftime("%Y-%m-%d %H:%M:%S")
        }
        
        return data if prix else None

    except Exception as e:
        print(f"   ❌ erreur {url[:50]}... : {e}")
        return None


# =========================
# SCRAPER LISTING
# =========================
def scrape_annonces(max_ads=20):
    """Scrape les annonces de voitures depuis Avito"""
    base_url = "https://www.avito.ma/fr/maroc/voitures"
    page = 1
    all_data = []
    seen_urls = set()
    
    print(f"\n🎯 Objectif: {max_ads} annonces de voitures\n")
    
    while len(all_data) < max_ads and page <= 10:
        url = f"{base_url}?o={page}" if page > 1 else base_url
        print(f"\n📄 Page {page}: {url}")
        
        try:
            driver.get(url)
            time.sleep(3)
            
            soup = BeautifulSoup(driver.page_source, "html.parser")
            
            # Chercher TOUS les liens
            all_links = soup.find_all('a', href=True)
            
            # Filtrer pour ne garder que les URLs d'annonces de voitures
            car_urls = []
            for a in all_links:
                href = a['href']
                if href.startswith('/'):
                    full_url = "https://www.avito.ma" + href
                else:
                    full_url = href
                
                if is_valid_car_url(full_url) and full_url not in seen_urls:
                    seen_urls.add(full_url)
                    car_urls.append(full_url)
            
            print(f"   → {len(car_urls)} annonces trouvées sur cette page")
            
            if not car_urls:
                print("   ⚠️ Aucune annonce trouvée, vérification...")
                # Debug: afficher les premiers liens trouvés
                sample_links = [a['href'] for a in all_links[:10] if 'annonce' in a['href']]
                print(f"   Exemples de liens: {sample_links[:3]}")
            
            for i, ad_url in enumerate(car_urls):
                if len(all_data) >= max_ads:
                    break
                
                print(f"\n   [{i+1}/{len(car_urls)}] Scraping...")
                data = get_car_details(ad_url)
                
                if data:
                    all_data.append(data)
                    print(f"      ✅ {data['titre'][:40] if data['titre'] else '?'} - {data['prix']:,} DH")
                else:
                    print(f"      ❌ Pas de prix, ignoré")
                
                time.sleep(random.uniform(2, 4))  # Pause aléatoire
            
            page += 1
            
        except Exception as e:
            print(f"   ❌ Erreur sur la page {page}: {e}")
            page += 1
    
    return all_data


# =========================
# RUN
# =========================
if __name__ == "__main__":
    print("\n📡 Démarrage du scraping...")
    
    cars = scrape_annonces(max_ads=10)
    
    if cars:
        df = pd.DataFrame(cars)
        df.to_csv("avito_voitures.csv", index=False, encoding="utf-8-sig")
        
        print("\n" + "="*70)
        print(f"✅ SUCCÈS! {len(df)} annonces sauvegardées")
        print("📁 Fichier: avito_voitures.csv")
        print("\n📊 APERÇU:")
        print(df[['titre', 'prix', 'annee', 'kilometrage', 'transmission', 'carburant']].head())
        
        print(f"\n💰 STATISTIQUES:")
        print(f"   Prix moyen: {df['prix'].mean():,.0f} DH")
        print(f"   Prix min: {df['prix'].min():,.0f} DH")
        print(f"   Prix max: {df['prix'].max():,.0f} DH")
    else:
        print("\n❌ Aucune annonce extraite")
        print("\n💡 Suggestions:")
        print("   1. Avito peut avoir bloqué votre IP")
        print("   2. Attendez 5 minutes et réessayez")
        print("   3. Ou utilisez Moteur.ma pour la suite")

driver.quit()
print("\n🏁 Terminé")