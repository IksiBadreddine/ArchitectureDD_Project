"""
Scraper pour Espacevoiture.com - Version finale
Correction de l'erreur NoneType + sauvegarde progressive
Exécution: uv run python scraper_espacevoiture_final.py
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
import os

print("="*70)
print("🚗 SCRAPER ESPACEVOITURE.COM - VERSION FINALE")
print("📡 Correction erreur NoneType + sauvegarde progressive")
print("   Appuyez sur Ctrl+C pour arrêter proprement")
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
        self.toutes_annonces = []
        self.filename = None
    
    def clean_price(self, text: str) -> Optional[int]:
        """Nettoie le prix - retourne None si pas de prix"""
        if not text:
            return None
        match = re.search(r'(\d[\d\s]*\d?)', text)
        if match:
            try:
                return int(match.group(1).replace(' ', ''))
            except:
                return None
        return None
    
    def clean_number(self, text: str) -> Optional[int]:
        if not text:
            return None
        match = re.search(r'(\d[\d\s]*\d?)', text)
        if match:
            try:
                return int(match.group(1).replace(' ', ''))
            except:
                return None
        return None
    
    def save_checkpoint(self):
        """Sauvegarde immédiate des données collectées"""
        if self.toutes_annonces:
            if not self.filename:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                self.filename = f"espacevoiture_final_{timestamp}.csv"
            
            df = pd.DataFrame(self.toutes_annonces)
            df.to_csv(self.filename, index=False, encoding="utf-8-sig")
            print(f"\n   💾 CHECKPOINT: {len(self.toutes_annonces)} annonces sauvegardées")
    
    def safe_format_price(self, prix):
        """Sécurise l'affichage du prix"""
        if prix is None:
            return "Prix non dispo"
        try:
            return f"{prix:,} DH"
        except:
            return "Prix invalide"
    
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
            
            # Titre
            if listing_data and listing_data.get('titre'):
                titre_complet = listing_data['titre']
            else:
                breadcrumb = soup.select('.breadcrumb a, .fil_ariane a')
                if breadcrumb and len(breadcrumb) >= 2:
                    titre_complet = f"{breadcrumb[-2].text} {breadcrumb[-1].text}"
                else:
                    title_tag = soup.find('title')
                    titre_complet = title_tag.text.strip() if title_tag else None
            
            details['titre'] = titre_complet
            
            # Marque et modèle
            if titre_complet:
                titre_clean = re.sub(r' - .*$', '', titre_complet)
                titre_clean = re.sub(r' \| .*$', '', titre_clean)
                mots = titre_clean.split()
                
                if len(mots) >= 2:
                    details['marque'] = mots[0]
                    details['modele'] = ' '.join(mots[1:])
                elif len(mots) == 1:
                    details['marque'] = mots[0]
                    details['modele'] = None
            
            # Prix
            price_elem = (soup.select_one('.prix') or 
                         soup.select_one('#rightContainer dd[style*="color:#F00"]') or
                         soup.select_one('.price'))
            if price_elem:
                details['prix'] = self.clean_price(price_elem.get_text(strip=True))
            
            if not details.get('prix') and listing_data and listing_data.get('prix'):
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
            
            # Infos du listing
            if listing_data:
                if listing_data.get('annee') and not details.get('annee'):
                    details['annee'] = listing_data['annee']
                if listing_data.get('kilometrage') and not details.get('kilometrage'):
                    details['kilometrage'] = listing_data['kilometrage']
            
            # Caractéristiques
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
    
    def scrape_listing_page(self, page_num: int = 1, get_details: bool = True) -> List[Dict]:
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
            rows = soup.select('#resultContainer tr')
            
            annonces_page = []
            for row in rows:
                prix_elem = row.select_one('.prix')
                if not prix_elem:
                    continue
                
                modele_elem = row.select_one('p.descriptif a')
                annee_elem = row.select_one('.annee')
                km_elem = row.select_one('.km')
                
                if modele_elem and prix_elem:
                    titre = modele_elem.get_text(strip=True)
                    lien = modele_elem.get('href')
                    full_url = urljoin(self.base_url, lien) if lien else None
                    
                    prix = self.clean_price(prix_elem.get_text(strip=True))
                    
                    # Ignorer les annonces sans prix (comme "Appeler pour le prix")
                    if prix is None:
                        print(f"   ⏭️ Ignoré: {titre[:35]} (pas de prix)")
                        continue
                    
                    annonce = {
                        'titre': titre,
                        'prix': prix,
                        'annee': self.clean_number(annee_elem.get_text(strip=True)) if annee_elem else None,
                        'kilometrage': self.clean_number(km_elem.get_text(strip=True)) if km_elem else None,
                        'url': full_url,
                        'source': 'espacevoiture.com',
                        'date_scraping': datetime.now().isoformat()
                    }
                    
                    # Récupération des détails
                    if get_details and full_url:
                        print(f"   → Détails: {titre[:35]}...")
                        details = self.get_ad_details(full_url, listing_data=annonce)
                        if details:
                            annonce.update(details)
                            prix_aff = self.safe_format_price(annonce.get('prix'))
                            print(f"      ✅ Marque: {details.get('marque', 'N/A')} | Prix: {prix_aff}")
                        else:
                            print(f"      ⚠️ Pas de détails")
                        time.sleep(random.uniform(0.5, 1))
                    
                    annonces_page.append(annonce)
                    prix_aff = self.safe_format_price(annonce['prix'])
                    print(f"   ✅ {titre[:35]} - {prix_aff}")
            
            print(f"   → {len(annonces_page)} annonces sur cette page")
            return annonces_page
            
        except Exception as e:
            print(f"   ❌ Erreur: {e}")
            return []
    
    def scrape_all_pages(self, max_pages: int = 310, get_details: bool = True, save_every: int = 10) -> List[Dict]:
        """Scrape plusieurs pages avec sauvegarde progressive"""
        toutes_annonces = []
        
        if max_pages > 904:
            max_pages = 904
        
        print(f"\n🎯 Scraping de {max_pages} pages maximum")
        print(f"💾 Sauvegarde automatique toutes les {save_every} pages")
        
        for page in range(1, max_pages + 1):
            print(f"\n{'='*50}")
            print(f"🔄 PAGE {page}/{max_pages}")
            
            annonces_page = self.scrape_listing_page(page, get_details=get_details)
            
            if annonces_page:
                toutes_annonces.extend(annonces_page)
                self.toutes_annonces = toutes_annonces
                print(f"\n   📊 Total actuel: {len(toutes_annonces)} annonces")
                
                # Sauvegarde toutes les X pages
                if page % save_every == 0:
                    self.save_checkpoint()
            else:
                print(f"\n   ⚠️ Aucune annonce sur cette page")
                # Continue quand même (la page peut être vide mais la suivante non)
            
            # Sauvegarde à la dernière page
            if page == max_pages:
                self.save_checkpoint()
            
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
    print("⚠️  Appuyez sur Ctrl+C pour arrêter proprement\n")
    
    # ========== CONFIGURATION ==========
    NB_PAGES = 400     # ← Nombre de pages (commence avec 50)
    GET_DETAILS = True  # ← True pour toutes les infos
    SAVE_EVERY = 10     # ← Sauvegarde toutes les X pages
    # ===================================
    
    print(f"🎯 Configuration:")
    print(f"   Pages: {NB_PAGES}")
    print(f"   Détails: {GET_DETAILS}")
    print(f"   Sauvegarde: toutes les {SAVE_EVERY} pages")
    
    try:
        annonces = scraper.scrape_all_pages(
            max_pages=NB_PAGES, 
            get_details=GET_DETAILS,
            save_every=SAVE_EVERY
        )
        
        if annonces:
            print("\n" + "="*70)
            print(f"✅ SUCCÈS! {len(annonces)} annonces sauvegardées")
            print(f"📁 Fichier: {scraper.filename}")
            
            df = pd.DataFrame(annonces)
            print("\n📊 APERÇU DES DONNÉES:")
            cols = ['marque', 'modele', 'prix', 'annee', 'kilometrage', 'ville', 'transmission', 'carburant']
            existing_cols = [c for c in cols if c in df.columns]
            print(df[existing_cols].head(15).to_string())
            
            if 'prix' in df.columns:
                prix_valides = df[df['prix'].notna()]['prix']
                if len(prix_valides) > 0:
                    print(f"\n💰 PRIX MOYEN: {prix_valides.mean():,.0f} DH")
            
            if 'marque' in df.columns:
                print(f"\n🏭 TOP MARQUES:")
                marques_valides = df[df['marque'].notna() & (df['marque'] != 'voiture')]
                for marque, count in marques_valides['marque'].value_counts().head(10).items():
                    prix_moyen = df[df['marque'] == marque]['prix'].mean()
                    print(f"   {marque}: {count} annonces - {prix_moyen:,.0f} DH")
        
        else:
            print("\n❌ Aucune annonce extraite")
    
    except KeyboardInterrupt:
        print("\n\n🛑 ARRÊT DEMANDÉ")
        print(f"💾 Sauvegarde des {len(scraper.toutes_annonces)} annonces...")
        scraper.save_checkpoint()
        print(f"✅ Données sauvegardées dans {scraper.filename}")

print("\n🏁 Scraping terminé")