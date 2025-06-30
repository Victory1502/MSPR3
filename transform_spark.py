# transform_spark.py - Version PySpark FINALE
from pyspark.sql import SparkSession
from pyspark.sql.functions import avg, min, max, desc, col  # Import sélectif pour éviter les conflits
from pyspark.sql.types import *
from minio import Minio
import json
import sys
from datetime import datetime
import builtins  # Pour accéder aux fonctions Python natives

def create_spark_session():
    spark = SparkSession.builder \
        .appName("GoodAir-Transform-Spark") \
        .config("spark.sql.execution.arrow.pyspark.enabled", "false") \
        .config("spark.serializer", "org.apache.spark.serializer.KryoSerializer") \
        .config("spark.sql.adaptive.enabled", "false") \
        .config("spark.python.worker.reuse", "false") \
        .config("spark.executorEnv.PYTHONPATH", "C:/Users/dimbo/Documents/Master 1 data ingenieur/MSPR3/environement/Scripts/python.exe") \
        .master("local[1]") \
        .getOrCreate()
    
    spark.sparkContext.setLogLevel("WARN")
    return spark

def log(message):
    print(f"[SPARK-TRANSFORM] {message}")
    sys.stdout.flush()

def retrieve_and_transform_spark():
    log("Démarrage de la transformation Spark")
    
    spark = create_spark_session()
    
    try:
        # Configuration MinIO
        minio_client = Minio(
            "localhost:9000",
            access_key="minio",
            secret_key="minio123",
            secure=False
        )
        
        bucket_name = "goodair-raw"
        
        if not minio_client.bucket_exists(bucket_name):
            log(f"Le bucket {bucket_name} n'existe pas")
            return
        
        # Récupération des objets du bucket
        objects = list(minio_client.list_objects(bucket_name, recursive=True))
        log(f"Nombre d'objets trouvés: {len(objects)}")
        
        # Filtrer pour les fichiers all_cities
        city_files = [obj.object_name for obj in objects if "all_cities_" in obj.object_name]
        
        if not city_files:
            log("Aucun fichier de données consolidées trouvé")
            return
        
        # Prendre le fichier le plus récent
        latest_file = sorted(city_files, reverse=True)[0]
        log(f"Fichier le plus récent: {latest_file}")
        
        # Télécharger et parser le contenu
        data = minio_client.get_object(bucket_name, latest_file)
        content = data.read().decode('utf-8')
        file_json = json.loads(content)
        
        city_data_list = file_json.get("villes", [])
        log(f"Données récupérées pour {len(city_data_list)} villes")
        
        # Définition du schéma pour les données transformées
        transformed_schema = StructType([
            StructField("ville", StringType(), True),
            StructField("latitude", DoubleType(), True),
            StructField("longitude", DoubleType(), True),
            StructField("timestamp_meteo", StringType(), True),
            StructField("temperature_k", DoubleType(), True),
            StructField("temperature_c", DoubleType(), True),
            StructField("temperature_ressentie_k", DoubleType(), True),
            StructField("temperature_ressentie_c", DoubleType(), True),
            StructField("pression", IntegerType(), True),
            StructField("humidite", IntegerType(), True),
            StructField("condition_meteo", StringType(), True),
            StructField("description_meteo", StringType(), True),
            StructField("visibilite", IntegerType(), True),
            StructField("vitesse_vent", DoubleType(), True),
            StructField("direction_vent", IntegerType(), True),
            StructField("couverture_nuageuse", IntegerType(), True),
            StructField("aqi", IntegerType(), True),
            StructField("polluant_dominant", StringType(), True),
            StructField("pm25", DoubleType(), True),
            StructField("pm10", DoubleType(), True),
            StructField("o3", DoubleType(), True),
            StructField("no2", DoubleType(), True),
            StructField("horodatage_aqi", StringType(), True)
        ])
        
        # Fonction de transformation des données
        def transform_city_data(city_data):
            """Transforme les données d'une ville en format structuré"""
            try:
                # Fonction helper pour conversion sécurisée
                def safe_float(value):
                    """Convertit en float de manière sécurisée"""
                    if value is None or value == 'N/A' or value == '':
                        return None
                    try:
                        return float(value)
                    except (ValueError, TypeError):
                        return None
                
                def safe_int(value):
                    """Convertit en int de manière sécurisée"""
                    if value is None or value == 'N/A' or value == '':
                        return None
                    try:
                        return int(value)
                    except (ValueError, TypeError):
                        return None
                
                # Extraction des informations de base
                ville = city_data.get('ville', 'N/A')
                latitude = city_data.get('latitude', None)
                longitude = city_data.get('longitude', None)
                timestamp = city_data.get('timestamp_extraction', 'N/A')
                
                # Extraction des données météo
                meteo_info = city_data.get('meteo', {})
                main_info = meteo_info.get('main', {})
                
                temp_k = safe_float(main_info.get('temp'))
                # CORRECTION: Utilisation de builtins.round() au lieu de la fonction PySpark round()
                temp_c = builtins.round(temp_k - 273.15, 1) if temp_k is not None else None
                feels_like_k = safe_float(main_info.get('feels_like'))
                feels_like_c = builtins.round(feels_like_k - 273.15, 1) if feels_like_k is not None else None
                
                weather_info = meteo_info.get('weather', [{}])[0] if meteo_info.get('weather') else {}
                wind_info = meteo_info.get('wind', {})
                clouds_info = meteo_info.get('clouds', {})
                
                # Extraction des données de qualité d'air
                air_info = city_data.get('qualite_air', {})
                air_data = air_info.get('data', {})
                iaqi_data = air_data.get('iaqi', {})
                time_info = air_data.get('time', {})
                
                return (
                    ville,
                    safe_float(latitude),
                    safe_float(longitude),
                    timestamp,
                    temp_k,
                    temp_c,
                    feels_like_k,
                    feels_like_c,
                    safe_int(main_info.get('pressure')),
                    safe_int(main_info.get('humidity')),
                    weather_info.get('main'),
                    weather_info.get('description'),
                    safe_int(meteo_info.get('visibility')),
                    safe_float(wind_info.get('speed')),
                    safe_int(wind_info.get('deg')),
                    safe_int(clouds_info.get('all')),
                    safe_int(air_data.get('aqi')),
                    air_data.get('dominentpol'),
                    safe_float(iaqi_data.get('pm25', {}).get('v')) if isinstance(iaqi_data.get('pm25'), dict) else safe_float(iaqi_data.get('pm25')),
                    safe_float(iaqi_data.get('pm10', {}).get('v')) if isinstance(iaqi_data.get('pm10'), dict) else safe_float(iaqi_data.get('pm10')),
                    safe_float(iaqi_data.get('o3', {}).get('v')) if isinstance(iaqi_data.get('o3'), dict) else safe_float(iaqi_data.get('o3')),
                    safe_float(iaqi_data.get('no2', {}).get('v')) if isinstance(iaqi_data.get('no2'), dict) else safe_float(iaqi_data.get('no2')),
                    time_info.get('iso')
                )
            except Exception as e:
                log(f"Erreur lors de la transformation pour {city_data.get('ville', 'Unknown')}: {str(e)}")
                return None
        
        # Transformation des données
        log("Transformation des données en cours...")
        transformed_data = []
        for city_data in city_data_list:
            result = transform_city_data(city_data)
            if result:
                transformed_data.append(result)
        
        if not transformed_data:
            log("Aucune donnée transformée disponible")
            return
        
        # Création du DataFrame Spark
        df_spark = spark.createDataFrame(transformed_data, transformed_schema)
        log(f"DataFrame Spark créé avec {df_spark.count()} lignes")
        
        # Affichage des statistiques
        log("=== STATISTIQUES DES DONNÉES TRANSFORMÉES ===")
        df_spark.describe().show()
        
        # Affichage des données par catégorie
        log("=== ÉCHANTILLON DES DONNÉES TRANSFORMÉES ===")
        
        # Informations de base
        log("Informations de base:")
        df_spark.select("ville", "latitude", "longitude", "timestamp_meteo").show(truncate=False)
        
        # Données météo principales
        log("Données météorologiques principales:")
        df_spark.select(
            "ville", "temperature_c", "temperature_ressentie_c", 
            "pression", "humidite", "condition_meteo"
        ).show(truncate=False)
        
        # Données de qualité d'air
        log("Données de qualité d'air:")
        df_spark.select(
            "ville", "aqi", "polluant_dominant", "pm25", "pm10", "o3", "no2"
        ).show(truncate=False)
        
        # Sauvegarde en CSV local
        log("Sauvegarde en CSV...")
        
        # Collecte des données pour sauvegarde locale
        pandas_df = df_spark.toPandas()
        
        # 1. Sauvegarde dans le répertoire courant (Windows)
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        csv_local_path = f"donnees_spark_transformees_{timestamp}.csv"
        
        try:
            import pandas as pd
            import os
            
            pandas_df.to_csv(csv_local_path, index=False)
            log(f"✅ Données sauvegardées localement: {csv_local_path}")
            log(f"📁 Répertoire: {os.getcwd()}")
        except Exception as e:
            log(f"❌ Erreur lors de la sauvegarde locale: {str(e)}")
        
        # 2. Sauvegarde legacy (chemin Airflow - pour compatibilité)
        csv_path = "/opt/airflow/project/donnees_completes.csv"
        try:
            if os.path.exists(csv_path):
                df_old = pd.read_csv(csv_path)
                df_concat = pd.concat([df_old, pandas_df], ignore_index=True)
                df_concat = df_concat.drop_duplicates()
                df_concat.to_csv(csv_path, index=False)
            else:
                pandas_df.to_csv(csv_path, index=False)
            
            log(f"✅ Données sauvegardées (legacy): {csv_path}")
        except Exception as e:
            log(f"⚠️ Sauvegarde legacy échouée (normal sur Windows): {str(e)}")
        
        # Sauvegarde en Parquet dans MinIO
        try:
            parquet_path = f"s3a://{bucket_name}/transformed_data_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            df_spark.write.mode("overwrite").parquet(parquet_path)
            log(f"Données transformées sauvegardées en Parquet: {parquet_path}")
        except Exception as e:
            log(f"Erreur lors de la sauvegarde Parquet: {str(e)}")
        
        # Analytics avancées avec Spark
        log("=== ANALYSES AVANCÉES SPARK ===")
        
        # Température moyenne par ville
        temp_stats = df_spark.groupBy("ville").agg(
            avg("temperature_c").alias("temp_moyenne"),
            min("temperature_c").alias("temp_min"),
            max("temperature_c").alias("temp_max")
        ).orderBy(desc("temp_moyenne"))
        
        log("Statistiques de température par ville:")
        temp_stats.show()
        
        # Qualité d'air par ville
        air_stats = df_spark.groupBy("ville").agg(
            avg("aqi").alias("aqi_moyen"),
            avg("pm25").alias("pm25_moyen"),
            avg("pm10").alias("pm10_moyen")
        ).orderBy("aqi_moyen")
        
        log("Statistiques de qualité d'air par ville:")
        air_stats.show()
        
        # Détection des villes avec pollution élevée
        high_pollution = df_spark.filter(
            (col("aqi") > 100) | (col("pm25") > 35) | (col("pm10") > 50)
        ).select("ville", "aqi", "pm25", "pm10")
        
        if high_pollution.count() > 0:
            log("⚠️ Villes avec pollution élevée détectées:")
            high_pollution.show()
        else:
            log("✅ Aucune pollution élevée détectée")
        
        log("Transformation Spark terminée avec succès")
        
    except Exception as e:
        log(f"Erreur lors de la transformation Spark: {str(e)}")
        import traceback
        log(traceback.format_exc())
        raise
    finally:
        spark.stop()

if __name__ == "__main__":
    try:
        retrieve_and_transform_spark()
    except Exception as e:
        log(f"ERREUR FATALE: {str(e)}")
        sys.exit(1)