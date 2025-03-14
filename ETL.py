import psycopg2
from psycopg2.extras import execute_values
from minio import Minio
from minio.error import S3Error
import json
from io import BytesIO
import pandas as pd
from datetime import datetime

# Configuration MinIO
minio_client = Minio(
    "localhost:9000",
    access_key="minio",
    secret_key="minio123",
    secure=False
)

# Configuration PostgreSQL
pg_config = {
    "host": "localhost",
    "port": 15432,
    "database": "mspr3",
    "user": "admin",
    "password": "admin123"
}

bucket_name = "meteo-villes"

def create_tables(conn):
    """Crée les tables nécessaires si elles n'existent pas déjà"""
    cursor = conn.cursor()
    
    # Table pour les villes
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS villes (
        id SERIAL PRIMARY KEY,
        nom VARCHAR(100) NOT NULL,
        latitude DOUBLE PRECISION NOT NULL,
        longitude DOUBLE PRECISION NOT NULL,
        UNIQUE(nom)
    )
    """)
    
    # Table pour les données météo
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS meteo (
        id SERIAL PRIMARY KEY,
        ville_id INTEGER REFERENCES villes(id),
        date_releve TIMESTAMP NOT NULL,
        temperature DOUBLE PRECISION,
        temperature_ressentie DOUBLE PRECISION,
        temperature_min DOUBLE PRECISION,
        temperature_max DOUBLE PRECISION,
        pression INTEGER,
        humidite INTEGER,
        visibilite INTEGER,
        vitesse_vent DOUBLE PRECISION,
        direction_vent INTEGER,
        rafale_vent DOUBLE PRECISION,
        nuages_pourcentage INTEGER,
        description_meteo VARCHAR(100),
        lever_soleil TIMESTAMP,
        coucher_soleil TIMESTAMP
    )
    """)
    
    # Table pour la qualité de l'air
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS qualite_air (
        id SERIAL PRIMARY KEY,
        ville_id INTEGER REFERENCES villes(id),
        date_releve TIMESTAMP NOT NULL,
        aqi INTEGER,
        polluant_dominant VARCHAR(20),
        pm25 DOUBLE PRECISION,
        pm10 DOUBLE PRECISION,
        o3 DOUBLE PRECISION,
        no2 DOUBLE PRECISION
    )
    """)
    
    # Table pour les prévisions de qualité d'air
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS previsions_qualite_air (
        id SERIAL PRIMARY KEY,
        ville_id INTEGER REFERENCES villes(id),
        date_prevision DATE NOT NULL,
        type_polluant VARCHAR(20) NOT NULL,
        valeur_moyenne DOUBLE PRECISION,
        valeur_min DOUBLE PRECISION,
        valeur_max DOUBLE PRECISION
    )
    """)
    
    conn.commit()
    cursor.close()

def insert_ville(conn, nom, latitude, longitude):
    """Insère une ville dans la base de données ou récupère son ID si elle existe déjà"""
    cursor = conn.cursor()
    cursor.execute("""
    INSERT INTO villes (nom, latitude, longitude)
    VALUES (%s, %s, %s)
    ON CONFLICT (nom) DO UPDATE 
        SET latitude = EXCLUDED.latitude, 
            longitude = EXCLUDED.longitude
    RETURNING id
    """, (nom, latitude, longitude))
    
    ville_id = cursor.fetchone()[0]
    conn.commit()
    cursor.close()
    return ville_id

def insert_meteo(conn, ville_id, meteo_data):
    """Insère les données météo pour une ville"""
    cursor = conn.cursor()
    
    # Extraire les données météo
    main = meteo_data.get("main", {})
    wind = meteo_data.get("wind", {})
    clouds = meteo_data.get("clouds", {})
    weather = meteo_data.get("weather", [{}])[0] if meteo_data.get("weather") else {}
    sys = meteo_data.get("sys", {})
    
    # Convertir les timestamps en datetime
    dt = datetime.fromtimestamp(meteo_data.get("dt", 0))
    sunrise = datetime.fromtimestamp(sys.get("sunrise", 0)) if sys.get("sunrise") else None
    sunset = datetime.fromtimestamp(sys.get("sunset", 0)) if sys.get("sunset") else None
    
    cursor.execute("""
    INSERT INTO meteo (
        ville_id, date_releve, temperature, temperature_ressentie, 
        temperature_min, temperature_max, pression, humidite, 
        visibilite, vitesse_vent, direction_vent, rafale_vent, 
        nuages_pourcentage, description_meteo, lever_soleil, coucher_soleil
    ) VALUES (
        %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
    )
    """, (
        ville_id, dt, 
        main.get("temp") - 273.15 if main.get("temp") else None,  # Conversion Kelvin -> Celsius
        main.get("feels_like") - 273.15 if main.get("feels_like") else None,
        main.get("temp_min") - 273.15 if main.get("temp_min") else None,
        main.get("temp_max") - 273.15 if main.get("temp_max") else None,
        main.get("pressure"),
        main.get("humidity"),
        meteo_data.get("visibility"),
        wind.get("speed"),
        wind.get("deg"),
        wind.get("gust"),
        clouds.get("all"),
        weather.get("description"),
        sunrise,
        sunset
    ))
    
    conn.commit()
    cursor.close()

def insert_qualite_air(conn, ville_id, air_data):
    """Insère les données de qualité d'air pour une ville"""
    cursor = conn.cursor()
    
    # Extraire les données de qualité d'air
    data = air_data.get("data", {})
    if not data:
        return
    
    iaqi = data.get("iaqi", {})
    time_data = data.get("time", {})
    
    # Convertir le timestamp en datetime
    dt = datetime.fromtimestamp(time_data.get("v", 0)) if time_data.get("v") else datetime.now()
    
    cursor.execute("""
    INSERT INTO qualite_air (
        ville_id, date_releve, aqi, polluant_dominant, pm25, pm10, o3, no2
    ) VALUES (
        %s, %s, %s, %s, %s, %s, %s, %s
    )
    """, (
        ville_id, dt, 
        data.get("aqi"),
        data.get("dominentpol"),
        iaqi.get("pm25", {}).get("v") if iaqi.get("pm25") else None,
        iaqi.get("pm10", {}).get("v") if iaqi.get("pm10") else None,
        iaqi.get("o3", {}).get("v") if iaqi.get("o3") else None,
        iaqi.get("no2", {}).get("v") if iaqi.get("no2") else None
    ))
    
    conn.commit()
    cursor.close()

def insert_previsions_air(conn, ville_id, air_data):
    """Insère les prévisions de qualité d'air"""
    cursor = conn.cursor()
    
    # Extraire les prévisions
    data = air_data.get("data", {})
    if not data:
        return
    
    forecast = data.get("forecast", {})
    daily = forecast.get("daily", {})
    
    # Liste pour stocker les données à insérer en masse
    values = []
    
    # Traiter chaque type de polluant
    polluants = ["pm25", "pm10", "o3", "uvi"]
    
    for polluant in polluants:
        if polluant not in daily:
            continue
        
        for prev in daily[polluant]:
            date_str = prev.get("day")
            if not date_str:
                continue
                
            date_prev = datetime.strptime(date_str, "%Y-%m-%d").date()
            values.append((
                ville_id,
                date_prev,
                polluant,
                prev.get("avg"),
                prev.get("min"),
                prev.get("max")
            ))
    
    # Insertion en masse si des données existent
    if values:
        execute_values(cursor, """
        INSERT INTO previsions_qualite_air (
            ville_id, date_prevision, type_polluant, valeur_moyenne, valeur_min, valeur_max
        ) VALUES %s
        """, values)
    
    conn.commit()
    cursor.close()

def main():
    try:
        # Connexion à PostgreSQL
        conn = psycopg2.connect(**pg_config)
        print("Connexion à PostgreSQL réussie")
        
        # Création des tables
        create_tables(conn)
        print("Tables créées avec succès")
        
        # Récupération de la liste des objets dans le bucket MinIO
        objects = minio_client.list_objects(bucket_name)
        
        for obj in objects:
            try:
                # Récupération de l'objet
                response = minio_client.get_object(bucket_name, obj.object_name)
                data = json.loads(response.read().decode('utf-8'))
                
                # Traitement des données
                ville = data.get("ville")
                latitude = data.get("latitude")
                longitude = data.get("longitude")
                meteo_data = data.get("meteo")
                air_data = data.get("qualite_air")
                
                if ville and latitude and longitude:
                    # Insérer ou mettre à jour la ville
                    ville_id = insert_ville(conn, ville, latitude, longitude)
                    print(f"Ville traitée: {ville} (ID: {ville_id})")
                    
                    # Insérer les données météo
                    if meteo_data:
                        insert_meteo(conn, ville_id, meteo_data)
                        print(f"Données météo insérées pour {ville}")
                    
                    # Insérer les données de qualité d'air
                    if air_data:
                        insert_qualite_air(conn, ville_id, air_data)
                        print(f"Données de qualité d'air insérées pour {ville}")
                        
                        # Insérer les prévisions de qualité d'air
                        insert_previsions_air(conn, ville_id, air_data)
                        print(f"Prévisions de qualité d'air insérées pour {ville}")
                
                response.close()
                response.release_conn()
                
            except Exception as e:
                print(f"Erreur lors du traitement de {obj.object_name}: {e}")
        
        # Fermeture de la connexion
        conn.close()
        print("Traitement terminé avec succès")
        
    except S3Error as e:
        print(f"Erreur MinIO: {e}")
    except psycopg2.Error as e:
        print(f"Erreur PostgreSQL: {e}")
    except Exception as e:
        print(f"Erreur inattendue: {e}")

if __name__ == "__main__":
    main()