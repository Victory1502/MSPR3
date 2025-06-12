import pandas as pd
import psycopg2
from psycopg2 import sql
import sys
import os
from datetime import datetime
import logging

# Configuration du logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def log(message: str):
    """Fonction de logging unifiée"""
    logger.info(message)
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] {message}")

class DataLoader:
    """Chargeur de données vers PostgreSQL"""
    
    def __init__(self, 
                 host: str = "localhost",
                 port: int = 15432,
                 database: str = "mspr3",
                 user: str = "admin",
                 password: str = "admin123"):
        """Initialisation avec les paramètres de connexion"""
        self.connection_params = {
            "host": host,
            "port": port,
            "database": database,
            "user": user,
            "password": password
        }
        self.conn = None
        self.cur = None

    def connect(self):
        """Établir la connexion à PostgreSQL"""
        try:
            print(self.connection_params)
            self.conn = psycopg2.connect(**self.connection_params)
            self.cur = self.conn.cursor()
            log("✅ Connexion à PostgreSQL établie avec succès")
        except Exception as e:
            log(f"❌ Erreur de connexion à PostgreSQL: {str(e)}")
            raise

    def close(self):
        """Fermer la connexion"""
        if self.cur:
            self.cur.close()
        if self.conn:
            self.conn.close()
            log("Connexion à PostgreSQL fermée")

    def create_tables(self):
        """Créer les tables nécessaires"""
        try:
            # Table pour les données météo
            self.cur.execute("""
                CREATE TABLE IF NOT EXISTS meteo_data (
                    id SERIAL PRIMARY KEY,
                    ville VARCHAR(100),
                    latitude FLOAT,
                    longitude FLOAT,
                    temperature FLOAT,
                    temperature_ressentie FLOAT,
                    pression FLOAT,
                    humidite INTEGER,
                    condition_meteo VARCHAR(100),
                    description_meteo TEXT,
                    visibilite INTEGER,
                    vitesse_vent FLOAT,
                    direction_vent INTEGER,
                    couverture_nuages INTEGER,
                    timestamp_extraction TIMESTAMP
                )
            """)

            # Table pour les données de qualité d'air
            self.cur.execute("""
                CREATE TABLE IF NOT EXISTS air_quality_data (
                    id SERIAL PRIMARY KEY,
                    ville VARCHAR(100),
                    aqi INTEGER,
                    polluant_dominant VARCHAR(50),
                    pm25 FLOAT,
                    pm10 FLOAT,
                    o3 FLOAT,
                    no2 FLOAT,
                    timestamp_extraction TIMESTAMP
                )
            """)

            self.conn.commit()
            log("✅ Tables créées avec succès")
        except Exception as e:
            self.conn.rollback()
            log(f"❌ Erreur lors de la création des tables: {str(e)}")
            raise

    def load_data(self, data_file: str = "test.csv"):
        """Charger les données depuis le CSV vers PostgreSQL"""
        try:
            # Lecture du fichier CSV
            df = pd.read_csv(data_file, encoding='latin1')
            log(f"📊 Données lues depuis {data_file}: {len(df)} enregistrements")

            # Préparation des données météo
            meteo_data = []
            for _, row in df.iterrows():
                meteo_record = (
                    row['Ville'],
                    row['Latitude'],
                    row['Longitude'],
                    row['Température (°C)'] if row['Température (°C)'] != 'N/A' else None,
                    row['Température ressentie (°C)'] if row['Température ressentie (°C)'] != 'N/A' else None,
                    row['Pression (hPa)'] if row['Pression (hPa)'] != 'N/A' else None,
                    row['Humidité (%)'] if row['Humidité (%)'] != 'N/A' else None,
                    row['Condition météo'],
                    row['Description météo'],
                    row['Visibilité (m)'] if row['Visibilité (m)'] != 'N/A' else None,
                    row['Vitesse du vent (m/s)'] if row['Vitesse du vent (m/s)'] != 'N/A' else None,
                    row['Direction du vent (°)'] if row['Direction du vent (°)'] != 'N/A' else None,
                    row['Couverture nuageuse (%)'] if row['Couverture nuageuse (%)'] != 'N/A' else None,
                    datetime.strptime(row['Timestamp'], '%Y-%m-%d %H:%M:%S')
                )
                meteo_data.append(meteo_record)

            # Insertion des données météo
            self.cur.executemany("""
                INSERT INTO meteo_data (
                    ville, latitude, longitude, temperature, temperature_ressentie,
                    pression, humidite, condition_meteo, description_meteo,
                    visibilite, vitesse_vent, direction_vent, couverture_nuages,
                    timestamp_extraction
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, meteo_data)

            # Préparation des données de qualité d'air
            air_data = []
            for _, row in df.iterrows():
                air_record = (
                    row['Ville'],
                    row['AQI'] if row['AQI'] != 'N/A' else None,
                    row['Polluant dominant'],
                    row['PM2.5'] if row['PM2.5'] != 'N/A' else None,
                    row['PM10'] if row['PM10'] != 'N/A' else None,
                    row['O3'] if row['O3'] != 'N/A' else None,
                    row['NO2'] if row['NO2'] != 'N/A' else None,
                    datetime.strptime(row['Timestamp'], '%Y-%m-%d %H:%M:%S')
                )
                air_data.append(air_record)

            # Insertion des données de qualité d'air
            self.cur.executemany("""
                INSERT INTO air_quality_data (
                    ville, aqi, polluant_dominant, pm25, pm10, o3, no2,
                    timestamp_extraction
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            """, air_data)

            self.conn.commit()
            log(f"✅ Données chargées avec succès: {len(df)} enregistrements")

        except Exception as e:
            self.conn.rollback()
            log(f"❌ Erreur lors du chargement des données: {str(e)}")
            raise

def main():
    """Fonction principale"""
    log("=" * 60)
    log("🔄 CHARGEMENT DES DONNÉES VERS POSTGRESQL")
    log("=" * 60)

    loader = None
    try:
        # Initialisation du chargeur
        loader = DataLoader()
        
        # Connexion à la base de données
        loader.connect()
        
        # Création des tables
        loader.create_tables()
        
        # Chargement des données
        loader.load_data()
        
        log("✅ Processus de chargement terminé avec succès")
        
    except Exception as e:
        log(f"❌ Erreur lors du processus de chargement: {str(e)}")
        sys.exit(1)
        
    finally:
        if loader:
            loader.close()

if __name__ == "__main__":
    main()
