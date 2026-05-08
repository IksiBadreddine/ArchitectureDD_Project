-- ============================================================
-- DATA WAREHOUSE - MARCHÉ AUTOMOBILE MAROCAIN
-- Base de données analytique (Gold Layer)
-- ============================================================

-- 1. TABLE DIMENSION: Marques
CREATE TABLE IF NOT EXISTS dim_marque (
    id_marque SERIAL PRIMARY KEY,
    code_marque VARCHAR(20) UNIQUE NOT NULL,
    nom_marque VARCHAR(50) NOT NULL,
    pays_origine VARCHAR(50),
    segment VARCHAR(20), -- Luxe, Premium, Grand Public
    date_insertion TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 2. TABLE DIMENSION: Villes
CREATE TABLE IF NOT EXISTS dim_ville (
    id_ville SERIAL PRIMARY KEY,
    nom_ville VARCHAR(50) NOT NULL UNIQUE,  /* ← AJOUT DE UNIQUE */
    region VARCHAR(50),
    population INTEGER,
    date_insertion TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 3. TABLE DIMENSION: Temps
CREATE TABLE IF NOT EXISTS dim_temps (
    id_temps SERIAL PRIMARY KEY,
    date_annonce DATE NOT NULL,
    annee INTEGER,
    mois INTEGER,
    trimestre INTEGER,
    semaine INTEGER,
    jour_semaine VARCHAR(10),
    mois_nom VARCHAR(20)
);

-- 4. TABLE FAITS: Annonces
CREATE TABLE IF NOT EXISTS fait_annonces (
    id_annonce SERIAL PRIMARY KEY,
    id_marque INTEGER REFERENCES dim_marque(id_marque),
    id_ville INTEGER REFERENCES dim_ville(id_ville),
    id_temps INTEGER REFERENCES dim_temps(id_temps),
    source VARCHAR(50),
    prix NUMERIC(10,2),
    kilometrage INTEGER,
    annee_vehicule INTEGER,
    age_vehicule INTEGER,
    carburant VARCHAR(20),
    transmission VARCHAR(20),
    nb_options INTEGER,
    url VARCHAR(500),
    score_qualite INTEGER,
    date_ingestion TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- ============================================================
-- VUES ANALYTIQUES
-- ============================================================

-- Vue 1: Prix moyen par marque
CREATE OR REPLACE VIEW v_prix_moyen_marque AS
SELECT 
    m.nom_marque,
    COUNT(f.id_annonce) AS nb_annonces,
    ROUND(AVG(f.prix), 0) AS prix_moyen,
    MIN(f.prix) AS prix_min,
    MAX(f.prix) AS prix_max,
    ROUND(AVG(f.kilometrage), 0) AS km_moyen
FROM fait_annonces f
JOIN dim_marque m ON f.id_marque = m.id_marque
GROUP BY m.nom_marque
ORDER BY prix_moyen DESC;

-- Vue 2: Distribution par année du véhicule
CREATE OR REPLACE VIEW v_distribution_annees AS
SELECT 
    f.annee_vehicule,
    COUNT(f.id_annonce) AS nb_annonces,
    ROUND(AVG(f.prix), 0) AS prix_moyen
FROM fait_annonces f
WHERE f.annee_vehicule IS NOT NULL
GROUP BY f.annee_vehicule
ORDER BY f.annee_vehicule DESC;

-- Vue 3: Top villes par volume d'annonces
CREATE OR REPLACE VIEW v_top_villes AS
SELECT 
    v.nom_ville,
    COUNT(f.id_annonce) AS nb_annonces,
    ROUND(AVG(f.prix), 0) AS prix_moyen
FROM fait_annonces f
JOIN dim_ville v ON f.id_ville = v.id_ville
GROUP BY v.nom_ville
ORDER BY nb_annonces DESC
LIMIT 10;

-- Vue 4: Répartition par carburant
CREATE OR REPLACE VIEW v_repartition_carburant AS
SELECT 
    f.carburant,
    COUNT(f.id_annonce) AS nb_annonces,
    ROUND(AVG(f.prix), 0) AS prix_moyen,
    ROUND(AVG(f.kilometrage), 0) AS km_moyen
FROM fait_annonces f
GROUP BY f.carburant
ORDER BY nb_annonces DESC;

-- Vue 5: Relation prix / kilométrage
CREATE OR REPLACE VIEW v_prix_vs_km AS
SELECT 
    CASE 
        WHEN f.kilometrage < 50000 THEN 'Moins de 50k km'
        WHEN f.kilometrage < 100000 THEN '50k-100k km'
        WHEN f.kilometrage < 150000 THEN '100k-150k km'
        WHEN f.kilometrage < 200000 THEN '150k-200k km'
        ELSE 'Plus de 200k km'
    END AS tranche_km,
    COUNT(f.id_annonce) AS nb_annonces,
    ROUND(AVG(f.prix), 0) AS prix_moyen,
    MIN(f.prix) AS prix_min,
    MAX(f.prix) AS prix_max
FROM fait_annonces f
GROUP BY tranche_km
ORDER BY MIN(f.kilometrage);

-- Vue 6: Prix par transmission
CREATE OR REPLACE VIEW v_prix_transmission AS
SELECT 
    f.transmission,
    COUNT(f.id_annonce) AS nb_annonces,
    ROUND(AVG(f.prix), 0) AS prix_moyen
FROM fait_annonces f
GROUP BY f.transmission;

-- ============================================================
-- INDEX POUR PERFORMANCES
-- ============================================================

CREATE INDEX IF NOT EXISTS idx_fait_marque ON fait_annonces(id_marque);
CREATE INDEX IF NOT EXISTS idx_fait_ville ON fait_annonces(id_ville);
CREATE INDEX IF NOT EXISTS idx_fait_temps ON fait_annonces(id_temps);
CREATE INDEX IF NOT EXISTS idx_fait_prix ON fait_annonces(prix);
CREATE INDEX IF NOT EXISTS idx_fait_annee ON fait_annonces(annee_vehicule);
CREATE INDEX IF NOT EXISTS idx_dim_ville_nom ON dim_ville(nom_ville);
CREATE INDEX IF NOT EXISTS idx_dim_marque_nom ON dim_marque(nom_marque);

-- ============================================================
-- INSERTS DES VALEURS DEFAULT
-- ============================================================

INSERT INTO dim_marque (code_marque, nom_marque, pays_origine) VALUES
('AUTRE', 'Autre', NULL),
('DACIA', 'Dacia', 'Roumanie'),
('RENAULT', 'Renault', 'France'),
('PEUGEOT', 'Peugeot', 'France'),
('CITROEN', 'Citroën', 'France'),
('VOLKSWAGEN', 'Volkswagen', 'Allemagne'),
('BMW', 'BMW', 'Allemagne'),
('MERCEDES', 'Mercedes', 'Allemagne'),
('AUDI', 'Audi', 'Allemagne'),
('TOYOTA', 'Toyota', 'Japon'),
('HYUNDAI', 'Hyundai', 'Corée du Sud'),
('KIA', 'Kia', 'Corée du Sud'),
('FORD', 'Ford', 'États-Unis'),
('OPEL', 'Opel', 'Allemagne'),
('VOLVO', 'Volvo', 'Suède')
ON CONFLICT (code_marque) DO NOTHING;

INSERT INTO dim_ville (nom_ville, region) VALUES
('Casablanca', 'Casablanca-Settat'),
('Rabat', 'Rabat-Salé-Kénitra'),
('Tanger', 'Tanger-Tétouan-Al Hoceïma'),
('Marrakech', 'Marrakech-Safi'),
('Fès', 'Fès-Meknès'),
('Agadir', 'Souss-Massa'),
('Tétouan', 'Tanger-Tétouan-Al Hoceïma'),
('Meknès', 'Fès-Meknès'),
('Oujda', 'Oriental')
ON CONFLICT (nom_ville) DO NOTHING;

-- ============================================================
-- RÉSUMÉ DES TABLES CRÉÉES
-- ============================================================
SELECT '✅ Data Warehouse initialisé avec succès!' AS status;