# extract_pyspark.py
from pyspark.sql import SparkSession
from pyspark.sql.functions import udf, col, lit, current_timestamp
from pyspark.sql.types import StructType, StructField, StringType, DoubleType, MapType
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

def get_meteo_data(lat, lon):
    """UDF pour récupérer les données météo"""
    meteo_api = "https://api.openweathermap.org/data/2.5/weather?lat={lat}&lon={lon}&appid=80f2502929bbdbaf3072277eb280a83f"
    meteo_url = meteo_api.format(lat=lat, lon=lon)
    try:
        meteo_response = requests.get(meteo_url, timeout=10)
        if meteo_response.status_code == 200:
            return json.dumps(meteo_response.json())
        else:
            return json.dumps({"error": "Impossible de récupérer les données météo"})
    except Exception as e:
        return json.dumps({"error": str(e)})

def get_air_quality_data(lat, lon):
    """UDF pour récupérer les données de qualité d'air"""
    air_api = "https://api.waqi.info/feed/geo:{lat};{lon}/?token=ca9559f64030829280e1efe135d52fab54ca3d6e"
    air_url = air_api.format(lat=lat, lon=lon)
    try:
        air_response = requests.get(air_url, timeout=10)
        if air_response.status_code == 200:
            return json.dumps(air_response.json())
        else:
            return json.dumps({"error": "Impossible de récupérer les données de qualité d'air"})
    except Exception as e:
        return json.dumps({"error": str(e)})

def extract_and_store():
    log("Démarrage de l'extraction des données avec PySpark")
    
    # Initialisation de Spark
    spark = SparkSession.builder \
        .appName("GoodAir Data Extraction") \
        .master("local[*]") \
        .config("spark.sql.execution.arrow.pyspark.enabled", "true") \
        .getOrCreate()
    
    # Configuration du niveau de log
    spark.sparkContext.setLogLevel("WARN")
    
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
    
    # Création du schéma
    schema = StructType([
        StructField("ville", StringType(), False),
        StructField("latitude", DoubleType(), False),
        StructField("longitude", DoubleType(), False)
    ])
    
    # Création du DataFrame Spark
    villes_df = spark.createDataFrame(villes_data, schema=schema)
    log(f"DataFrame Spark créé avec {villes_df.count()} villes")
    
    # Enregistrement des UDF
    get_meteo_udf = udf(get_meteo_data, StringType())
    get_air_udf = udf(get_air_quality_data, StringType())
    
    # Configuration MinIO
    try:
        log("Tentative de connexion à MinIO")
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
            log(f"Bucket {bucket_name} créé avec succès")
        
        # Ajout des colonnes avec les données météo et qualité d'air
        enriched_df = villes_df \
            .withColumn("meteo_data", get_meteo_udf(col("latitude"), col("longitude"))) \
            .withColumn("air_quality_data", get_air_udf(col("latitude"), col("longitude"))) \
            .withColumn("timestamp_extraction", lit(datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
        
        # Cache du DataFrame pour éviter de refaire les appels API
        enriched_df.cache()
        
        # Collecte des données pour le stockage
        collected_rows = enriched_df.collect()
        
        # Stockage individuel pour chaque ville
        for row in collected_rows:
            ville = row["ville"]
            log(f"Sauvegarde des données pour {ville}")
            
            # Création de l'objet JSON pour la ville
            city_data = {
                "ville": ville,
                "latitude": row["latitude"],
                "longitude": row["longitude"],
                "meteo": json.loads(row["meteo_data"]),
                "qualite_air": json.loads(row["air_quality_data"]),
                "timestamp_extraction": row["timestamp_extraction"]
            }
            
            # Nom du fichier
            file_name = f"{ville}_{datetime.now().strftime('%Y_%m_%d_%H_%M')}.json"
            
            # Conversion en JSON et BytesIO
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
        all_cities_data = []
        for row in collected_rows:
            city_data = {
                "ville": row["ville"],
                "latitude": row["latitude"],
                "longitude": row["longitude"],
                "meteo": json.loads(row["meteo_data"]),
                "qualite_air": json.loads(row["air_quality_data"]),
                "timestamp_extraction": row["timestamp_extraction"]
            }
            all_cities_data.append(city_data)
        
        if all_cities_data:
            all_data = {
                "villes": all_cities_data,
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "nombre_villes": len(all_cities_data)
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
        
        # Optionnel : Sauvegarde directe en format Parquet pour optimisation
        try:
            # Sauvegarde en Parquet dans MinIO via S3
            parquet_path = f"s3a://goodair-raw/parquet/{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            
            # Configuration pour S3 (MinIO)
            spark.conf.set("spark.hadoop.fs.s3a.endpoint", "http://localhost:9000")
            spark.conf.set("spark.hadoop.fs.s3a.access.key", "minio")
            spark.conf.set("spark.hadoop.fs.s3a.secret.key", "minio123")
            spark.conf.set("spark.hadoop.fs.s3a.path.style.access", "true")
            spark.conf.set("spark.hadoop.fs.s3a.impl", "org.apache.hadoop.fs.s3a.S3AFileSystem")
            
            # Écriture en Parquet
            enriched_df.write \
                .mode("overwrite") \
                .parquet(parquet_path)
            
            log(f"Données sauvegardées en format Parquet: {parquet_path}")
        except Exception as e:
            log(f"Impossible de sauvegarder en Parquet (dépendances S3 manquantes): {str(e)}")
        
        # Affichage des statistiques
        log("=== Statistiques de l'extraction ===")
        log(f"Nombre total de villes traitées: {enriched_df.count()}")
        enriched_df.select("ville", "timestamp_extraction").show(truncate=False)
        
        log("Extraction terminée avec succès")
        
        # Arrêt de Spark
        spark.stop()
        
    except Exception as e:
        log(f"Erreur lors de l'extraction: {str(e)}")
        spark.stop()
        raise

if __name__ == "__main__":
    try:
        extract_and_store()
    except Exception as e:
        log(f"ERREUR: {str(e)}")
        import traceback
        log(traceback.format_exc())
        sys.exit(1)