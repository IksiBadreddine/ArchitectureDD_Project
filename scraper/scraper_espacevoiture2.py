"""
Scraper pour Espacevoiture.com - Version corrigée
Extraction correcte de la marque et du modèle
Exécution: uv run python scraper_espacevoiture_corrected.py
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
print("🚗 SCRAPER ESPACEVOITURE.COM - VERSION CORRIGÉE")
print("📡 Extraction correcte de la marque et du modèle")
print("="*70)

class EspaceVoitureScraper:
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'fr,fr-FR;q=0.8,en;q=0.5',
        })
        self.base_url = "https://www.espacevoiture.com"
    
    def clean_price(self, text: str) -> Optional[int]:
        if not text:
            return None
        match = re.search(r'(\d[\d\s]*\d?)', text)
        if match:
            return int(match.group(1).replace(' ', ''))
        return None
    
    def clean_number(self, text: str) -> Optional[int]:
        if not text:
            return None
        match = re.search(r'(\d[\d\s]*\d?)', text)
        if match:
            return int(match.group(1).replace(' ', ''))
        return None
    
    def get_ad_details(self, url: str, listing_data: Dict = None) -> Dict:
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
            
            # ✅ CORRECTION 1: Titre depuis le lien ou depuis la page
            if listing_data and listing_data.get('titre'):
                titre_complet = listing_data['titre']
            else:
                # Alternative: chercher dans le breadcrumb ou le titre
                breadcrumb = soup.select('.breadcrumb a, .fil_ariane a')
                if breadcrumb and len(breadcrumb) >= 2:
                    titre_complet = f"{breadcrumb[-2].text} {breadcrumb[-1].text}"
                else:
                    title_tag = soup.find('title')
                    titre_complet = title_tag.text.strip() if title_tag else None
            
            details['titre'] = titre_complet
            
            # ✅ CORRECTION 2: Extraction marque et modèle depuis le titre
            if titre_complet:
                # Nettoyer le titre (enlever les parties indésirables)
                titre_clean = re.sub(r' - .*$', '', titre_complet)
                titre_clean = re.sub(r' \| .*$', '', titre_clean)
                mots = titre_clean.split()
                
                if len(mots) >= 2:
                    details['marque'] = mots[0]
                    details['modele'] = ' '.join(mots[1:])
                elif len(mots) == 1:
                    details['marque'] = mots[0]
                    details['modele'] = None
            
            # ✅ CORRECTION 3: Prix depuis plusieurs sources
            price_elem = (soup.select_one('.prix') or 
                         soup.select_one('#rightContainer dd[style*="color:#F00"]') or
                         soup.select_one('.price'))
            if price_elem:
                details['prix'] = self.clean_price(price_elem.get_text(strip=True))
            elif listing_data and listing_data.get('prix'):
                details['prix'] = listing_data['prix']
            
            # Date de l'annonce
            date_elem = soup.select_one('.dateAnnonce')
            if date_elem:
                date_match = re.search(r'(\d{2}/\d{2}/\d{4})', date_elem.text)
                if date_match:
                    details['date_annonce'] = date_match.group(1)
            
            # Ville
            ville_elem = (soup.select_one('#ficheContact dl:has(dt:contains("Ville")) dd a') or
                         soup.select_one('#ficheContact dl:has(dt:contains("Ville")) dd'))
            if ville_elem:
                details['ville'] = ville_elem.get_text(strip=True)
            
            # Année et kilométrage depuis listing si non trouvés
            if listing_data:
                if listing_data.get('annee') and not details.get('annee'):
                    details['annee'] = listing_data['annee']
                if listing_data.get('kilometrage') and not details.get('kilometrage'):
                    details['kilometrage'] = listing_data['kilometrage']
            
            # Extraction des caractéristiques
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
            
            # Trouver toutes les lignes d'annonces
            rows = soup.select('#resultContainer tr')
            
            annonces_page = []
            for row in rows:
                prix_elem = row.select_one('.prix')
                if not prix_elem:
                    continue
                
                # Extraire le modèle/lien
                modele_elem = row.select_one('p.descriptif a')
                annee_elem = row.select_one('.annee')
                km_elem = row.select_one('.km')
                
                if modele_elem and prix_elem:
                    titre = modele_elem.get_text(strip=True)
                    lien = modele_elem.get('href')
                    full_url = urljoin(self.base_url, lien) if lien else None
                    
                    annonce = {
                        'titre': titre,
                        'prix': self.clean_price(prix_elem.get_text(strip=True)),
                        'annee': self.clean_number(annee_elem.get_text(strip=True)) if annee_elem else None,
                        'kilometrage': self.clean_number(km_elem.get_text(strip=True)) if km_elem else None,
                        'url': full_url,
                        'source': 'espacevoiture.com',
                        'date_scraping': datetime.now().isoformat()
                    }
                    
                    annonces_page.append(annonce)
                    print(f"   ✅ {titre[:35]} - {annonce['prix']:,} DH")
            
            print(f"   → {len(annonces_page)} annonces sur cette page")
            return annonces_page
            
        except Exception as e:
            print(f"   ❌ Erreur: {e}")
            return []
    
    def scrape_all_pages(self, max_pages: int = 5, get_details: bool = True) -> List[Dict]:
        """Scrape plusieurs pages"""
        toutes_annonces = []
        
        if max_pages > 904:
            max_pages = 904
        
        print(f"\n🎯 Scraping de {max_pages} pages")
        
        for page in range(1, max_pages + 1):
            annonces_page = self.scrape_listing_page(page)
            
            if get_details:
                for i, annonce in enumerate(annonces_page):
                    if annonce.get('url'):
                        print(f"\n   [{i+1}/{len(annonces_page)}] Détails: {annonce['titre']}...")
                        details = self.get_ad_details(annonce['url'], listing_data=annonce)
                        if details:
                            annonce.update(details)
                            print(f"      ✅ Marque: {details.get('marque', 'N/A')} | Modèle: {details.get('modele', 'N/A')} | Ville: {details.get('ville', 'N/A')}")
                        time.sleep(random.uniform(0.5, 1))
            
            toutes_annonces.extend(annonces_page)
            
            if page < max_pages:
                delay = random.uniform(1, 2)
                print(f"\n   ⏳ Pause de {delay:.1f}s...")
                time.sleep(delay)
        
        return toutes_annonces

# =========================
# MAIN
# =========================
if __name__ == "__main__":
    scraper = EspaceVoitureScraper()
    
    print("\n📡 Démarrage du scraping...")
    
    # Configuration
    NB_PAGES =       # Commencer avec 3 pages pour tester
    GET_DETAILS = True
    
    print(f"🎯 Configuration: {NB_PAGES} pages, détails: {GET_DETAILS}")
    
    annonces = scraper.scrape_all_pages(max_pages=NB_PAGES, get_details=GET_DETAILS)
    
    if annonces:
        df = pd.DataFrame(annonces)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"espacevoiture_corrige_{timestamp}.csv"
        df.to_csv(filename, index=False, encoding="utf-8-sig")
        
        print("\n" + "="*70)
        print(f"✅ SUCCÈS! {len(df)} annonces sauvegardées")
        print(f"📁 Fichier: {filename}")
        
        print("\n📊 APERÇU DES DONNÉES CORRIGÉES:")
        cols = ['marque', 'modele', 'prix', 'annee', 'kilometrage', 'ville', 'transmission', 'carburant']
        print(df[[c for c in cols if c in df.columns]].head(15).to_string())
        
        print(f"\n💰 STATISTIQUES:")
        if 'prix' in df.columns:
            print(f"   Prix moyen: {df['prix'].mean():,.0f} DH")
        
        if 'marque' in df.columns:
            print(f"\n🏭 TOP MARQUES:")
            marques_valides = df[df['marque'].notna() & (df['marque'] != 'voiture')]
            for marque, count in marques_valides['marque'].value_counts().head(10).items():
                prix_moyen = df[df['marque'] == marque]['prix'].mean()
                print(f"   {marque}: {count} annonces - Prix moyen: {prix_moyen:,.0f} DH")
        
    else:
        print("\n❌ Aucune annonce extraite")

print("\n🏁 Scraping terminé")