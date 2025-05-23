# extract_simple.py

from Spark_session import get_spark_session
from pyspark.sql.types import StructType, StructField, StringType, DoubleType
from pyspark.sql.functions import udf, col
import requests
import json
from minio import Minio
from io import BytesIO
from datetime import datetime
import sys
import traceback

def log(message):
    print(f"[INFO] {message}")
    sys.stdout.flush()

# Fonction qui sera sérialisée et envoyée aux workers
def fetch_api_data(ville, lat, lon):
    """Fonction pure qui sera exécutée sur les workers Spark"""
    
    # Recréer les URLs dans la fonction (pas de variables globales)
    air_api = "https://api.waqi.info/feed/geo:{lat};{lon}/?token=ca9559f64030829280e1efe135d52fab54ca3d6e"
    meteo_api = "https://api.openweathermap.org/data/2.5/weather?lat={lat}&lon={lon}&appid=80f2502929bbdbaf3072277eb280a83f"
    
    try:
        meteo = requests.get(meteo_api.format(lat=lat, lon=lon), timeout=10).json()
    except Exception as e:
        meteo = {"error": str(e)}

    try:
        air = requests.get(air_api.format(lat=lat, lon=lon), timeout=10).json()
    except Exception as e:
        air = {"error": str(e)}

    # Retourner un dictionnaire sérialisable
    return {
        "ville": ville,
        "latitude": lat,
        "longitude": lon,
        "meteo": json.dumps(meteo),  # Sérialiser en string
        "qualite_air": json.dumps(air),  # Sérialiser en string
        "timestamp_extraction": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }

def extract_and_store():
    log("Démarrage de l'extraction des données (PySpark)")

    spark = get_spark_session()
    
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

    schema = StructType([
        StructField("ville", StringType(), True),
        StructField("latitude", DoubleType(), True),
        StructField("longitude", DoubleType(), True)
    ])

    villes_df = spark.createDataFrame(villes_data, schema=schema)
    log(f"DataFrame Spark créé avec {villes_df.count()} villes")

    # Créer l'UDF pour les appels API
    fetch_udf = udf(fetch_api_data, StringType())

    # MÉTHODE 1: Utiliser les RDD (approche corrigée)
    def process_row(row):
        return fetch_api_data(row['ville'], row['latitude'], row['longitude'])
    
    # Collecter les données avec map (les objets externes ne sont plus dans la fonction)
    log("Début des appels API via Spark...")
    collected_data_raw = villes_df.rdd.map(process_row).collect()
    
    # Reconvertir les JSON strings en objets Python
    collected_data = []
    for item in collected_data_raw:
        processed_item = {
            "ville": item["ville"],
            "latitude": item["latitude"], 
            "longitude": item["longitude"],
            "meteo": json.loads(item["meteo"]),
            "qualite_air": json.loads(item["qualite_air"]),
            "timestamp_extraction": item["timestamp_extraction"]
        }
        collected_data.append(processed_item)

    log(f"Données collectées pour {len(collected_data)} villes")

    # Initialiser MinIO client APRÈS la collecte Spark (dans le driver)
    minio_client = Minio(
        "localhost:9000",
        access_key="minio",
        secret_key="minio123",
        secure=False
    )

    bucket_name = "goodair-raw"
    if not minio_client.bucket_exists(bucket_name):
        log(f"Création du bucket {bucket_name}")
        minio_client.make_bucket(bucket_name)

    # Sauvegarder chaque ville individuellement
    for data in collected_data:
        try:
            ville = data["ville"]
            file_name = f"{ville}_{datetime.now().strftime('%Y_%m_%d_%H_%M')}.json"
            data_bytes = json.dumps(data, indent=2).encode('utf-8')
            minio_client.put_object(
                bucket_name,
                file_name,
                BytesIO(data_bytes),
                length=len(data_bytes)
            )
            log(f"Données pour {ville} sauvegardées avec succès")
        except Exception as e:
            log(f"Erreur de sauvegarde {ville} : {str(e)}")

    # Sauvegarde du fichier global
    try:
        all_data = {
            "villes": collected_data,
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
        all_data_json = json.dumps(all_data, indent=2).encode('utf-8')
        all_data_bytes = BytesIO(all_data_json)

        minio_client.put_object(
            bucket_name,
            f"all_cities_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
            all_data_bytes,
            length=len(all_data_json)
        )
        log("Fichier global sauvegardé avec succès")
    except Exception as e:
        log(f"Erreur lors de la sauvegarde du fichier global : {str(e)}")

    spark.stop()
    log("Extraction terminée avec succès")

if __name__ == "__main__":
    try:
        extract_and_store()
    except Exception as e:
        log(f"ERREUR: {str(e)}")
        log(traceback.format_exc())
        sys.exit(1)