"""
Scraper Moteur.ma - Version DIRECTE (sans dépendre d'un CSV existant)
1. Scrape les URLs depuis les pages listing
2. Pour chaque URL, scrape la page détail
3. Extrait TOUTES les informations (marque, modèle, année, km, transmission)
Exécution: uv run python scraper_moteur_direct.py
"""

import requests
from bs4 import BeautifulSoup
import pandas as pd
import re
import time
import random
from datetime import datetime
from typing import List, Dict, Optional

print("="*70)
print("🚗 SCRAPER MOTEUR.MA - VERSION DIRECTE")
print("📡 Scraping listing → pages détail → extraction complète")
print("="*70)

class MoteurMaDirectScraper:
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'fr,fr-FR;q=0.8,en;q=0.5',
        })
    
    def clean_price(self, text: str) -> Optional[int]:
        if not text:
            return None
        match = re.search(r'(\d[\d\s,]*\d)', str(text))
        if match:
            return int(match.group(1).replace(',', '').replace(' ', ''))
        return None
    
    def clean_number(self, text: str) -> Optional[int]:
        if not text:
            return None
        match = re.search(r'(\d[\d\s,]*\d)', str(text))
        if match:
            return int(match.group(1).replace(',', '').replace(' ', ''))
        return None
    
    def extract_all_details(self, soup) -> Dict:
        """Extrait TOUTES les informations du tableau (structure 4 colonnes)"""
        details = {}
        
        table = soup.find('table', class_='table-bordered')
        if not table:
            return details
        
        rows = table.find_all('tr')
        
        for row in rows:
            cols = row.find_all('td')
            
            # Structure à 4 colonnes: Label1, Valeur1, Label2, Valeur2
            if len(cols) == 4:
                label1 = cols[0].get_text(strip=True).replace(':', '').lower()
                value1 = cols[1].get_text(strip=True)
                label2 = cols[2].get_text(strip=True).replace(':', '').lower()
                value2 = cols[3].get_text(strip=True)
                
                details[label1] = value1 if value1 != 'N/A' else None
                details[label2] = value2 if value2 != 'N/A' else None
            
            # Structure à 2 colonnes
            elif len(cols) == 2:
                label = cols[0].get_text(strip=True).replace(':', '').lower()
                value = cols[1].get_text(strip=True)
                details[label] = value if value != 'N/A' else None
        
        return details
    
    def get_ad_details(self, url: str) -> Dict:
        """Récupère TOUS les détails d'une annonce"""
        try:
            response = self.session.get(url, timeout=15)
            if response.status_code != 200:
                return {}
            
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Structure de base
            details = {
                'url': url,
                'date_scraping': datetime.now().isoformat(),
                'source': 'moteur.ma',
            }
            
            # 1. Titre
            title_elem = soup.select_one('h1.ad-hero-title')
            details['titre'] = title_elem.get_text(strip=True).replace('\n', ' ') if title_elem else None
            
            # 2. Prix
            price_elem = soup.select_one('.ad-hero-price-col')
            details['prix'] = self.clean_price(price_elem.get_text(strip=True)) if price_elem else None
            
            # 3. Métadonnées (ville, date, vues)
            meta_items = soup.select('.ad-detail-meta__item')
            for item in meta_items:
                text = item.get_text(strip=True)
                icon = str(item)
                if 'fa-map-marker' in icon:
                    details['ville'] = text
                elif 'fa-calendar' in icon:
                    details['date_annonce'] = text
                elif 'fa-eye' in icon:
                    match = re.search(r'(\d+)', text)
                    details['vues'] = int(match.group(1)) if match else None
            
            # 4. Tableau des caractéristiques (la partie importante !)
            table_details = self.extract_all_details(soup)
            
            # Mapping des champs
            details['marque'] = table_details.get('marque')
            details['modele'] = table_details.get('modèle')
            details['annee'] = self.clean_number(table_details.get('année'))
            details['kilometrage'] = self.clean_number(table_details.get('kilométrage'))
            details['carburant'] = table_details.get('carburant')
            details['transmission'] = table_details.get('transmission')
            details['carrosserie'] = table_details.get('carrosserie')
            details['couleur'] = table_details.get('couleur')
            details['portes'] = table_details.get('nombre de portes')
            details['puissance_fiscale'] = table_details.get('puissance fiscale')
            
            # 5. Description
            desc_elem = soup.select_one('.mb-5 p')
            details['description'] = desc_elem.get_text(strip=True)[:1000] if desc_elem else None
            
            # 6. Options
            options = []
            option_items = soup.select('.col-12 .d-flex.align-items-center')
            for item in option_items:
                if 'fa-check' in str(item):
                    text = item.get_text(strip=True)
                    if text and len(text) < 50:
                        options.append(text)
            details['options'] = ', '.join(options[:20]) if options else None
            details['nb_options'] = len(options)
            
            return details
            
        except Exception as e:
            print(f"      ❌ Erreur: {e}")
            return {}
    
    def scrape_all(self, max_pages: int = 3, max_ads: int = 15) -> List[Dict]:
        """Scrape tout : listing → pages détail → extraction"""
        print("\n🔍 Étape 1: Récupération des URLs depuis les pages listing...")
        
        # Récupérer toutes les URLs
        all_urls = []
        
        for page in range(1, max_pages + 1):
            url = f"https://www.moteur.ma/fr/voitures-occasion?page={page}"
            print(f"   Page {page}...")
            
            try:
                response = self.session.get(url, timeout=15)
                soup = BeautifulSoup(response.content, 'html.parser')
                
                for a in soup.find_all('a', href=True):
                    href = a['href']
                    if '/detail-annonce/' in href:
                        if href.startswith('/'):
                            full_url = 'https://www.moteur.ma' + href
                        else:
                            full_url = href
                        if full_url not in all_urls:
                            all_urls.append(full_url)
                
                time.sleep(random.uniform(0.5, 1))
                
            except Exception as e:
                print(f"      ❌ Erreur page {page}: {e}")
        
        print(f"   → {len(all_urls)} URLs trouvées")
        
        # Limiter le nombre d'annonces
        urls_to_scrape = all_urls[:max_ads]
        print(f"   → {len(urls_to_scrape)} URLs seront scrapées")
        
        print("\n🔍 Étape 2: Extraction des détails...")
        
        annonces = []
        for i, url in enumerate(urls_to_scrape):
            print(f"\n   [{i+1}/{len(urls_to_scrape)}] {url.split('/')[-2]}")
            
            details = self.get_ad_details(url)
            if details and details.get('prix'):
                annonces.append(details)
                print(f"      ✅ {details.get('marque', '?')} {details.get('modele', '?')} - {details.get('prix'):,} DH - {details.get('annee', '?')} - {details.get('kilometrage', '?')} km - {details.get('transmission', '?')}")
            else:
                print(f"      ❌ Pas de prix, ignoré")
            
            time.sleep(random.uniform(1, 2))
        
        return annonces

# =========================
# MAIN
# =========================
if __name__ == "__main__":
    scraper = MoteurMaDirectScraper()
    
    print("\n📡 Démarrage du scraping direct...")
    annonces = scraper.scrape_all(max_pages=2, max_ads=10)
    
    if annonces:
        df = pd.DataFrame(annonces)
        
        # Réorganiser les colonnes
        cols_order = ['titre', 'marque', 'modele', 'prix', 'annee', 'kilometrage', 
                      'carburant', 'transmission', 'ville', 'vues', 'date_annonce',
                      'description', 'options', 'nb_options', 'url', 'date_scraping']
        
        cols_present = [c for c in cols_order if c in df.columns]
        df = df[cols_present]
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_file = f"moteur_ma_complet_{timestamp}.csv"
        df.to_csv(output_file, index=False, encoding="utf-8-sig")
        
        print("\n" + "="*70)
        print(f"✅ SUCCÈS! {len(df)} annonces avec détails complets")
        print(f"📁 Fichier: {output_file}")
        
        print("\n📊 APERÇU DES DONNÉES:")
        print(df[['marque', 'modele', 'prix', 'annee', 'kilometrage', 'transmission']].to_string())
        
        # Vérification
        print("\n" + "="*70)
        print("🔍 VÉRIFICATION:")
        print(f"   Marques: {df['marque'].tolist()}")
        print(f"   Modèles: {df['modele'].tolist()}")
        print(f"   Kilométrages: {df['kilometrage'].tolist()}")
        print(f"   Transmissions: {df['transmission'].tolist()}")
        
    else:
        print("\n❌ Aucune annonce extraite")

print("\n🏁 Scraping terminé")