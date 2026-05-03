"""
Scraper pour Espacevoiture.com - Marché automobile marocain
Exécution: uv run python scraper_espacevoiture.py
"""

import requests
from bs4 import BeautifulSoup
import pandas as pd
import re
import time
import random
from datetime import datetime
from typing import List, Dict, Optional
from urllib.parse import urljoin

print("="*70)
print("🚗 SCRAPER ESPACEVOITURE.COM - MARCHÉ AUTOMOBILE MAROCAIN")
print("📡 Extraction des annonces (904 pages, 9000+ annonces)")
print("="*70)

class EspaceVoitureScraper:
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'fr,fr-FR;q=0.8,en;q=0.5',
            'Referer': 'https://www.espacevoiture.com/',
        })
        self.base_url = "https://www.espacevoiture.com"
    
    def clean_price(self, text: str) -> Optional[int]:
        """Nettoie le prix (ex: '165 000 DHS' -> 165000)"""
        if not text:
            return None
        match = re.search(r'(\d[\d\s]*\d?)', text)
        if match:
            return int(match.group(1).replace(' ', ''))
        return None
    
    def clean_number(self, text: str) -> Optional[int]:
        """Nettoie un nombre (ex: '30 000 KM' -> 30000)"""
        if not text:
            return None
        match = re.search(r'(\d[\d\s]*\d?)', text)
        if match:
            return int(match.group(1).replace(' ', ''))
        return None
    
    def extract_marque_modele(self, title: str) -> tuple:
        """Extrait marque et modèle du titre"""
        parts = title.split()
        if len(parts) >= 2:
            return parts[0], ' '.join(parts[1:])
        return title, None
    
    def get_ad_details(self, url: str) -> Dict:
        """Récupère les détails complets d'une annonce"""
        try:
            response = self.session.get(url, timeout=15)
            if response.status_code != 200:
                return {}
            
            soup = BeautifulSoup(response.content, 'html.parser')
            
            details = {
                'url': url,
                'date_scraping': datetime.now().isoformat(),
                'source': 'espacevoiture.com'
            }
            
            # Informations de base
            title_elem = soup.select_one('h1')
            if title_elem:
                title = title_elem.get_text(strip=True)
                details['titre'] = title
                marque, modele = self.extract_marque_modele(title)
                details['marque'] = marque
                details['modele'] = modele
            
            # Prix
            price_elem = soup.select_one('.prix, #rightContainer dd[style*="color:#F00"]')
            if price_elem:
                details['prix'] = self.clean_price(price_elem.get_text(strip=True))
            
            # Date de l'annonce
            date_elem = soup.select_one('.dateAnnonce')
            if date_elem:
                date_match = re.search(r'(\d{2}/\d{2}/\d{4})', date_elem.text)
                if date_match:
                    details['date_annonce'] = date_match.group(1)
            
            # Ville
            ville_elem = soup.select_one('#ficheContact dl:has(dt:contains("Ville")) dd a')
            if ville_elem:
                details['ville'] = ville_elem.get_text(strip=True)
            
            # Extraction de toutes les caractéristiques du tableau #rightContainer
            right_container = soup.select_one('#rightContainer')
            if right_container:
                for dl in right_container.select('dl'):
                    dt = dl.select_one('dt')
                    dd = dl.select_one('dd')
                    if dt and dd:
                        label = dt.get_text(strip=True).lower()
                        value = dd.get_text(strip=True)
                        
                        if 'année' in label:
                            details['annee'] = self.clean_number(value)
                        elif 'kilométrage' in label:
                            details['kilometrage'] = self.clean_number(value)
                        elif 'boîte' in label or 'vitesse' in label:
                            details['transmission'] = value
                        elif 'énergie' in label:
                            details['carburant'] = value
                        elif 'puissance fiscale' in label:
                            details['puissance_fiscale'] = value
                        elif 'nb portes' in label:
                            details['portes'] = self.clean_number(value)
                        elif 'couleur extérieure' in label:
                            details['couleur'] = value
            
            return details
            
        except Exception as e:
            print(f"      ❌ Erreur détail: {e}")
            return {}
    
    def scrape_listing_page(self, page_num: int = 1) -> List[Dict]:
        """Scrape une page de listing"""
        if page_num == 1:
            url = "https://www.espacevoiture.com/voitures.html"
        else:
            url = f"https://www.espacevoiture.com/voitures/page{page_num}.html"
        
        print(f"\n📄 Page {page_num}: {url}")
        
        try:
            response = self.session.get(url, timeout=15)
            if response.status_code != 200:
                print(f"   ❌ HTTP {response.status_code}")
                return []
            
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Trouver toutes les lignes d'annonces dans le tableau
            rows = soup.select('#resultContainer tr')
            
            annonces_page = []
            for row in rows:
                # Vérifier si c'est une ligne d'annonce (a un prix)
                prix_elem = row.select_one('.prix')
                if not prix_elem:
                    continue
                
                # Extraire les infos de base
                modele_elem = row.select_one('p.descriptif a')
                annee_elem = row.select_one('.annee')
                km_elem = row.select_one('.km')
                
                if modele_elem and prix_elem:
                    # Lien vers le détail
                    lien = modele_elem.get('href')
                    if lien:
                        full_url = urljoin(self.base_url, lien)
                    else:
                        full_url = None
                    
                    annonce = {
                        'titre': modele_elem.get_text(strip=True),
                        'prix': self.clean_price(prix_elem.get_text(strip=True)),
                        'annee': self.clean_number(annee_elem.get_text(strip=True)) if annee_elem else None,
                        'kilometrage': self.clean_number(km_elem.get_text(strip=True)) if km_elem else None,
                        'url': full_url,
                        'source': 'espacevoiture.com',
                        'date_scraping': datetime.now().isoformat()
                    }
                    
                    annonces_page.append(annonce)
                    print(f"   ✅ {annonce['titre'][:30]} - {annonce['prix']:,} DH - {annonce['annee']} - {annonce['kilometrage']} km")
            
            print(f"   → {len(annonces_page)} annonces sur cette page")
            return annonces_page
            
        except Exception as e:
            print(f"   ❌ Erreur: {e}")
            return []
    
    def scrape_all_pages(self, max_pages: int = 10, get_details: bool = True) -> List[Dict]:
        """Scrape plusieurs pages"""
        toutes_annonces = []
        
        # Déterminer le nombre de pages
        if max_pages > 904:
            max_pages = 904
            print(f"\n📊 Limité à 904 pages (dernière page)")
        
        print(f"\n🎯 Scraping de {max_pages} pages")
        
        for page in range(1, max_pages + 1):
            annonces_page = self.scrape_listing_page(page)
            
            if get_details:
                # Pour chaque annonce, récupérer les détails
                for i, annonce in enumerate(annonces_page):
                    if annonce.get('url'):
                        print(f"\n   [{i+1}/{len(annonces_page)}] Détails pour {annonce['titre']}...")
                        details = self.get_ad_details(annonce['url'])
                        if details:
                            annonce.update(details)
                            print(f"      ✅ Ville: {details.get('ville', 'N/A')} | Transmission: {details.get('transmission', 'N/A')} | Carburant: {details.get('carburant', 'N/A')}")
                        time.sleep(random.uniform(0.5, 1))
            
            toutes_annonces.extend(annonces_page)
            
            # Pause entre les pages
            if page < max_pages:
                delay = random.uniform(1, 2)
                print(f"\n   ⏳ Pause de {delay:.1f}s avant page suivante...")
                time.sleep(delay)
        
        return toutes_annonces

# =========================
# MAIN
# =========================
if __name__ == "__main__":
    scraper = EspaceVoitureScraper()
    
    print("\n📡 Démarrage du scraping...")
    
    # Configuration
    NB_PAGES = 5  # À ajuster (max 904)
    GET_DETAILS = True  # True pour plus d'infos, False pour plus rapide
    
    print(f"🎯 Configuration: {NB_PAGES} pages, détails: {GET_DETAILS}")
    
    annonces = scraper.scrape_all_pages(max_pages=NB_PAGES, get_details=GET_DETAILS)
    
    if annonces:
        df = pd.DataFrame(annonces)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"espacevoiture_{timestamp}.csv"
        df.to_csv(filename, index=False, encoding="utf-8-sig")
        
        print("\n" + "="*70)
        print(f"✅ SUCCÈS! {len(df)} annonces sauvegardées")
        print(f"📁 Fichier: {filename}")
        
        print("\n📊 APERÇU DES DONNÉES:")
        cols = ['titre', 'prix', 'annee', 'kilometrage', 'ville', 'transmission', 'carburant']
        print(df[[c for c in cols if c in df.columns]].head(15).to_string())
        
        print(f"\n💰 STATISTIQUES:")
        if 'prix' in df.columns:
            print(f"   Prix moyen: {df['prix'].mean():,.0f} DH")
            print(f"   Prix min: {df['prix'].min():,.0f} DH")
            print(f"   Prix max: {df['prix'].max():,.0f} DH")
        
        if 'annee' in df.columns:
            print(f"\n📅 ANNÉES:")
            annee_counts = df[df['annee'].notna()]['annee'].value_counts().sort_index(ascending=False).head(10)
            for annee, count in annee_counts.items():
                print(f"   {int(annee)}: {count} annonces")
        
        if 'marque' in df.columns:
            print(f"\n🏭 TOP MARQUES:")
            for marque, count in df['marque'].value_counts().head(10).items():
                prix_moyen = df[df['marque'] == marque]['prix'].mean()
                print(f"   {marque}: {count} annonces - Prix moyen: {prix_moyen:,.0f} DH")
        
        if 'ville' in df.columns:
            print(f"\n📍 TOP VILLES:")
            for ville, count in df['ville'].value_counts().head(10).items():
                print(f"   {ville}: {count} annonces")
        
    else:
        print("\n❌ Aucune annonce extraite")

print("\n🏁 Scraping terminé")