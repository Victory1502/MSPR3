# extract.py
import pandas as pd
import requests
import json
from minio import Minio
from minio.error import S3Error
from io import BytesIO
from datetime import datetime
import sys
import os

def log(message):
    print(f"[INFO] {message}")
    sys.stdout.flush()

def extract_and_store():
    log("Démarrage de l'extraction des données")
    
    # Liste des villes avec leurs coordonnées
    villes_data = [
        ("Paris", 48.8566, 2.3522),
        ("Marseille", 43.2965, 5.3698),
        ("Lyon", 45.7640, 4.8357),
        ("Toulouse", 43.6047, 1.4442),
        ("Nice", 43.7102, 7.2620),
        ("Nantes", 47.2186, -1.5536),
        ("Strasbourg", 48.5734, 7.7521),
        ("Montpellier", 43.6117, 3.8777),
        ("Bordeaux", 44.8378, -0.5792),
        ("Lille", 50.6292, 3.0573),
        ("Rennes", 48.1173, -1.6778),
        ("Le Havre", 49.4944, 0.1079)
    ]
    
    # Création d'un DataFrame pandas (au lieu de Spark)
    villes_df = pd.DataFrame(villes_data, columns=["ville", "latitude", "longitude"])
    log(f"DataFrame des villes créé avec {len(villes_df)} villes")
    
    # APIs URLs
    air_api = "https://api.waqi.info/feed/geo:{lat};{lon}/?token=ca9559f64030829280e1efe135d52fab54ca3d6e"
    meteo_api = "https://api.openweathermap.org/data/2.5/weather?lat={lat}&lon={lon}&appid=80f2502929bbdbaf3072277eb280a83f"
    
    # Configuration MinIO
    try:
        log("Tentative de connexion à MinIO")
        minio_client = Minio(
            "localhost:9000",  # Ajustez si nécessaire à localhost:9000
            access_key="minio",
            secret_key="minio123",
            secure=False
        )
        
        bucket_name = "goodair-raw"
        if not minio_client.bucket_exists(bucket_name):
            log(f"Création du bucket {bucket_name}")
            minio_client.make_bucket(bucket_name)
            log(f"Bucket {bucket_name} créé avec succès")
        
        # Collecte des données
        collected_data = []
        for _, row in villes_df.iterrows():
            ville = row["ville"]
            lat = row["latitude"]
            lon = row["longitude"]
            
            log(f"Récupération des données pour {ville}")
            
            # Récupération des données météo
            meteo_url = meteo_api.format(lat=lat, lon=lon)
            try:
                meteo_response = requests.get(meteo_url, timeout=10)
                meteo_data = meteo_response.json() if meteo_response.status_code == 200 else {"error": "Impossible de récupérer les données météo"}
            except Exception as e:
                meteo_data = {"error": str(e)}
            
            # Récupération des données de qualité d'air
            air_url = air_api.format(lat=lat, lon=lon)
            try:
                air_response = requests.get(air_url, timeout=10)
                air_data = air_response.json() if air_response.status_code == 200 else {"error": "Impossible de récupérer les données de qualité d'air"}
            except Exception as e:
                air_data = {"error": str(e)}
            
            # Création d'un objet complet
            city_data = {
                "ville": ville,
                "latitude": lat,
                "longitude": lon,
                "meteo": meteo_data,
                "qualite_air": air_data,
                "timestamp_extraction": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }
            
            collected_data.append(city_data)
            
            # Stockage individuel pour chaque ville
            current_date = datetime.now().strftime("%Y-%m-%d")
            file_name = f"{ville}_{datetime.now().strftime('%Y_%m_%d_%H_%M')}.json"

            
            
            json_data = json.dumps(city_data, indent=2).encode('utf-8')
            byte_data = BytesIO(json_data)
            
            try:
                minio_client.put_object(
                    bucket_name,
                    file_name,
                    byte_data,
                    length=len(json_data)
                )
                log(f"Données pour {ville} sauvegardées avec succès")
            except Exception as e:
                log(f"Erreur lors de la sauvegarde des données pour {ville}: {str(e)}")
        
        # Stockage d'un fichier regroupant toutes les villes
        if collected_data:
            all_data = {
                "villes": collected_data,
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }
            
            all_data_json = json.dumps(all_data, indent=2).encode('utf-8')
            all_data_bytes = BytesIO(all_data_json)
            
            try:
                minio_client.put_object(
                    bucket_name,
                    f"all_cities_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
                    all_data_bytes,
                    length=len(all_data_json)
                )
                log("Fichier regroupant toutes les villes sauvegardé avec succès")
            except Exception as e:
                log(f"Erreur lors de la sauvegarde du fichier regroupant toutes les villes: {str(e)}")
        
        log("Extraction terminée avec succès")
        
    except Exception as e:
        log(f"Erreur lors de l'extraction: {str(e)}")
        raise
    
if __name__ == "__main__":
    try:
        extract_and_store()
    except Exception as e:
        log(f"ERREUR: {str(e)}")
        import traceback
        log(traceback.format_exc())
        sys.exit(1)