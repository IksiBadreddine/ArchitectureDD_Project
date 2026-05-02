"""
Scraper Moteur.ma - Version corrigée V2
Capture TOUTES les annonces des pages listing
Exécution: uv run python scraper_moteur_fixed_v2.py
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
print("🚗 SCRAPER MOTEUR.MA - VERSION CORRIGÉE V2")
print("📡 Capture TOUTES les annonces des pages listing")
print("="*70)

class MoteurMaFixedScraper:
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
        """Extrait TOUTES les informations du tableau"""
        details = {}
        
        table = soup.find('table', class_='table-bordered')
        if not table:
            return details
        
        rows = table.find_all('tr')
        
        for row in rows:
            cols = row.find_all('td')
            
            if len(cols) == 4:
                label1 = cols[0].get_text(strip=True).replace(':', '').lower()
                value1 = cols[1].get_text(strip=True)
                label2 = cols[2].get_text(strip=True).replace(':', '').lower()
                value2 = cols[3].get_text(strip=True)
                
                details[label1] = value1 if value1 != 'N/A' else None
                details[label2] = value2 if value2 != 'N/A' else None
            
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
            
            details = {
                'url': url,
                'date_scraping': datetime.now().isoformat(),
                'source': 'moteur.ma',
            }
            
            # Titre
            title_elem = soup.select_one('h1.ad-hero-title')
            details['titre'] = title_elem.get_text(strip=True).replace('\n', ' ') if title_elem else None
            
            # Prix
            price_elem = soup.select_one('.ad-hero-price-col')
            details['prix'] = self.clean_price(price_elem.get_text(strip=True)) if price_elem else None
            
            # Métadonnées
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
            
            # Tableau des caractéristiques
            table_details = self.extract_all_details(soup)
            
            details['marque'] = table_details.get('marque')
            details['modele'] = table_details.get('modèle')
            details['annee'] = self.clean_number(table_details.get('année'))
            details['kilometrage'] = self.clean_number(table_details.get('kilométrage'))
            details['carburant'] = table_details.get('carburant')
            details['transmission'] = table_details.get('transmission')
            details['carrosserie'] = table_details.get('carrosserie')
            details['couleur'] = table_details.get('couleur')
            
            # Description
            desc_elem = soup.select_one('.mb-5 p')
            details['description'] = desc_elem.get_text(strip=True)[:1000] if desc_elem else None
            
            # Options
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
    
    def scrape_all(self, max_pages: int = 10, max_ads: int = 200) -> List[Dict]:
        """Scrape TOUTES les annonces correctement"""
        print("\n🔍 Étape 1: Récupération des URLs depuis les pages listing...")
        
        all_urls = []
        
        for page in range(1, max_pages + 1):
            url = f"https://www.moteur.ma/fr/voitures-occasion?page={page}"
            print(f"   Page {page}...", end=" ")
            
            try:
                response = self.session.get(url, timeout=15)
                soup = BeautifulSoup(response.content, 'html.parser')
                
                # 🔧 CORRECTION IMPORTANTE 🔧
                # Chercher TOUS les liens qui contiennent "detail-annonce"
                # et qui sont dans des balises <a> à l'intérieur des divs d'annonces
                
                page_urls = []
                
                # Méthode 1: Chercher tous les liens "detail-annonce"
                for a in soup.find_all('a', href=True):
                    href = a['href']
                    if '/detail-annonce/' in href:
                        if href.startswith('/'):
                            full_url = 'https://www.moteur.ma' + href
                        else:
                            full_url = href
                        
                        # Nettoyer l'URL (enlever les paramètres)
                        full_url = full_url.split('?')[0]
                        
                        if full_url not in all_urls and full_url not in page_urls:
                            page_urls.append(full_url)
                
                # Méthode 2: Chercher dans les divs .inner (structure du carrousel)
                for inner in soup.select('.grid-carousel .inner, .bx-viewport .inner'):
                    link = inner.find('a', href=True)
                    if link and '/detail-annonce/' in link['href']:
                        href = link['href']
                        if href.startswith('/'):
                            full_url = 'https://www.moteur.ma' + href
                        else:
                            full_url = href
                        full_url = full_url.split('?')[0]
                        
                        if full_url not in all_urls and full_url not in page_urls:
                            page_urls.append(full_url)
                
                print(f"{len(page_urls)} nouvelles URLs")
                all_urls.extend(page_urls)
                
                if len(all_urls) >= max_ads:
                    print(f"\n   → Limite atteinte: {len(all_urls)} URLs trouvées")
                    break
                
                time.sleep(random.uniform(0.5, 1))
                
            except Exception as e:
                print(f"❌ Erreur: {e}")
        
        # Supprimer les doublons et limiter
        all_urls = list(set(all_urls))[:max_ads]
        
        print(f"\n   → TOTAL: {len(all_urls)} URLs uniques trouvées")
        
        if not all_urls:
            print("\n⚠️ Aucune URL trouvée! Vérification du HTML...")
            # Test avec la première page
            response = self.session.get("https://www.moteur.ma/fr/voitures-occasion", timeout=15)
            soup = BeautifulSoup(response.content, 'html.parser')
            # Chercher n'importe quel lien contenant detail-annonce
            sample_links = []
            for a in soup.find_all('a', href=True):
                if 'detail-annonce' in a['href']:
                    sample_links.append(a['href'])
            print(f"   Exemples de liens trouvés: {sample_links[:3]}")
            return []
        
        print("\n🔍 Étape 2: Extraction des détails...")
        
        annonces = []
        for i, url in enumerate(all_urls):
            print(f"\n   [{i+1}/{len(all_urls)}] {url.split('/')[-2]}")
            
            details = self.get_ad_details(url)
            if details and details.get('prix'):
                annonces.append(details)
                print(f"      ✅ {details.get('marque', '?')} {details.get('modele', '?')} - {details.get('prix'):,} DH - {details.get('annee', '?')} - {details.get('kilometrage', '?')} km")
            else:
                print(f"      ❌ Pas de prix, ignoré")
            
            # Pause aléatoire pour éviter la détection
            time.sleep(random.uniform(1, 2))
        
        return annonces

# =========================
# MAIN
# =========================
if __name__ == "__main__":
    scraper = MoteurMaFixedScraper()
    
    print("\n📡 Démarrage du scraping...")
    
    # 🔧 MODIFIE CES VALEURS SELON TES BESOINS 🔧
    NB_PAGES = 10      # Nombre de pages listing
    NB_ANNONCES = 200  # Nombre maximum d'annonces
    # ===========================================
    
    print(f"🎯 Configuration: {NB_PAGES} pages, maximum {NB_ANNONCES} annonces")
    
    annonces = scraper.scrape_all(max_pages=NB_PAGES, max_ads=NB_ANNONCES)
    
    if annonces:
        df = pd.DataFrame(annonces)
        
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
        
        print(f"\n💰 STATISTIQUES:")
        print(f"   Prix moyen: {df['prix'].mean():,.0f} DH")
        print(f"   Kilométrage moyen: {df['kilometrage'].mean():,.0f} km")
        
        print(f"\n🏭 RÉPARTITION PAR MARQUE:")
        print(df['marque'].value_counts())
        
    else:
        print("\n❌ Aucune annonce extraite")
        print("\n💡 SUGGESTION: Le site a peut-être changé sa structure HTML")
        print("   Exécutez: uv run python debug_moteur.py pour analyser")

print("\n🏁 Scraping terminé")