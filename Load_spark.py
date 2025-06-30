# Load_spark.py - Version PySpark avec VPS
from pyspark.sql import SparkSession
from pyspark.sql.functions import *
from pyspark.sql.types import *
import os
import sys
from datetime import datetime

def create_spark_session():
    """Création de la session Spark avec configurations pour PostgreSQL"""
    spark = SparkSession.builder \
        .appName("GoodAir-Load-Spark") \
        .config("spark.sql.adaptive.enabled", "true") \
        .config("spark.sql.adaptive.coalescePartitions.enabled", "true") \
        .config("spark.jars.packages", "org.postgresql:postgresql:42.7.0") \
        .getOrCreate()
    
    spark.sparkContext.setLogLevel("WARN")
    return spark

def log(message):
    print(f"[SPARK-LOAD] {message}")
    sys.stdout.flush()

def load_spark():
    log("Démarrage du chargement Spark")
    
    spark = create_spark_session()
    
    try:
        # Détection automatique de l'environnement et chemins adaptatifs
        csv_paths = [
            "donnees_completes.csv",
            "/opt/airflow/project/donnees_completes.csv",
            "/opt/airflow/donnees_completes.csv",
            "/opt/airflow/dags/donnees_completes.csv",
            "./project/donnees_completes.csv",
            os.path.join(os.getcwd(), "donnees_completes.csv"),
        ]
        
        csv_file = None
        for path in csv_paths:
            if os.path.exists(path):
                csv_file = path
                log(f"✅ Fichier CSV trouvé à : {csv_file}")
                break
        
        if csv_file is None:
            log("❌ Fichier 'donnees_completes.csv' introuvable.")
            log("📂 Chemins testés :")
            for i, path in enumerate(csv_paths, 1):
                log(f"   {i}. {path}")
            log(f"📍 Répertoire de travail actuel : {os.getcwd()}")
            
            raise FileNotFoundError("Fichier 'donnees_completes.csv' introuvable")
        
        # Lecture du fichier CSV avec Spark
        log(f"📖 Lecture du fichier CSV avec Spark : {csv_file}")
        
        # Définition du schéma pour optimiser la lecture
        csv_schema = StructType([
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
        
        # Lecture du CSV avec Spark
        df_spark = spark.read \
            .option("header", "true") \
            .option("encoding", "UTF-8") \
            .option("multiline", "true") \
            .option("escape", "\"") \
            .schema(csv_schema) \
            .csv(csv_file)
        
        log(f"📈 Données chargées avec Spark : {df_spark.count()} lignes, {len(df_spark.columns)} colonnes")
        
        # Détection de l'environnement
        is_docker = os.path.exists("/opt/airflow") or "AIRFLOW_HOME" in os.environ
        
        # Configuration des bases de données
        if is_docker:
            log("🐳 Environnement Docker détecté")
            db_url_local = "jdbc:postgresql://postgres:5432/mspr3"
        else:
            log("💻 Environnement local détecté")
            db_url_local = "jdbc:postgresql://localhost:15432/mspr3"
        
        db_url_cloud = "jdbc:postgresql://ep-curly-bread-abg9804h-pooler.eu-west-2.aws.neon.tech:5432/mspr3"
        db_url_vps = "jdbc:postgresql://158.178.196.156:5432/mspr3"
        
        # Propriétés de connexion
        db_properties_local = {
            "user": "admin",
            "password": "admin123",
            "driver": "org.postgresql.Driver",
            "stringtype": "unspecified"
        }
        
        db_properties_cloud = {
            "user": "mspr3_owner",
            "password": "npg_gIMFn84DuBpH",
            "driver": "org.postgresql.Driver",
            "stringtype": "unspecified",
            "ssl": "true",
            "sslmode": "require"
        }
        
        db_properties_vps = {
            "user": "postgres",
            "password": "admin123",
            "driver": "org.postgresql.Driver",
            "stringtype": "unspecified"
        }
        
        # Optimisations pour l'écriture
        df_optimized = df_spark \
            .coalesce(4) \
            .cache()  # Cache le DataFrame pour éviter de le recalculer
        
        log("🔧 DataFrame optimisé et mis en cache")
        
        # Validation des données avant insertion
        log("🔍 Validation des données...")
        
        # Compter les lignes avec des données valides
        valid_count = df_optimized.filter(
            col("ville").isNotNull() & 
            col("latitude").isNotNull() & 
            col("longitude").isNotNull()
        ).count()
        
        log(f"✅ {valid_count} lignes valides sur {df_optimized.count()} total")
        
        # Nettoyage des données (optionnel)
        df_clean = df_optimized.filter(
            col("ville").isNotNull() & 
            col("latitude").isNotNull() & 
            col("longitude").isNotNull()
        )
        
        # Affichage des statistiques avant chargement
        log("📊 Statistiques des données à charger:")
        df_clean.describe().show()
        
        # Sauvegarde en base locale/docker
        try:
            log("💾 Chargement en base locale/docker...")
            
            df_clean.write \
                .mode("append") \
                .option("batchsize", "1000") \
                .option("isolationLevel", "READ_COMMITTED") \
                .jdbc(db_url_local, "meteo_air_quality", properties=db_properties_local)
            
            env_type = "Docker" if is_docker else "local"
            log(f"✅ Données chargées dans la base {env_type} avec succès.")
            
        except Exception as e:
            log(f"⚠️ Erreur lors du chargement en base locale/docker : {e}")
            # Tentative de création de table si elle n'existe pas
            try:
                log("🔧 Tentative de création de la table...")
                df_clean.write \
                    .mode("overwrite") \
                    .jdbc(db_url_local, "meteo_air_quality", properties=db_properties_local)
                log("✅ Table créée et données chargées avec succès.")
            except Exception as e2:
                log(f"❌ Échec de création de table locale : {e2}")
        
        # Sauvegarde en base cloud
        try:
            log("🌐 Chargement en base cloud...")
            
            df_clean.write \
                .mode("append") \
                .option("batchsize", "1000") \
                .option("isolationLevel", "READ_COMMITTED") \
                .jdbc(db_url_cloud, "meteo_air_quality", properties=db_properties_cloud)
            
            log("✅ Données chargées dans la base cloud avec succès.")
            
        except Exception as e:
            log(f"⚠️ Erreur lors du chargement en base cloud : {e}")
            # Tentative de création de table si elle n'existe pas
            try:
                log("🔧 Tentative de création de la table cloud...")
                df_clean.write \
                    .mode("overwrite") \
                    .jdbc(db_url_cloud, "meteo_air_quality", properties=db_properties_cloud)
                log("✅ Table cloud créée et données chargées avec succès.")
            except Exception as e2:
                log(f"❌ Échec de création de table cloud : {e2}")
        
        # Sauvegarde en base VPS
        try:
            log("🖥️ Chargement en base VPS...")
            
            df_clean.write \
                .mode("append") \
                .option("batchsize", "1000") \
                .option("isolationLevel", "READ_COMMITTED") \
                .jdbc(db_url_vps, "meteo_air_quality", properties=db_properties_vps)
            
            log("✅ Données chargées dans la base VPS avec succès.")
            
        except Exception as e:
            log(f"⚠️ Erreur lors du chargement en base VPS : {e}")
            # Tentative de création de table si elle n'existe pas
            try:
                log("🔧 Tentative de création de la table VPS...")
                df_clean.write \
                    .mode("overwrite") \
                    .jdbc(db_url_vps, "meteo_air_quality", properties=db_properties_vps)
                log("✅ Table VPS créée et données chargées avec succès.")
            except Exception as e2:
                log(f"❌ Échec de création de table VPS : {e2}")
        
        # Analytics post-chargement avec Spark
        log("📈 Analyses post-chargement...")
        
        # Nombre de lignes par ville
        city_counts = df_clean.groupBy("ville").count().orderBy(desc("count"))
        log("Nombre d'enregistrements par ville:")
        city_counts.show()
        
        # Températures extrêmes
        temp_extremes = df_clean.select(
            min("temperature_c").alias("temp_min_globale"),
            max("temperature_c").alias("temp_max_globale"),
            avg("temperature_c").alias("temp_moyenne_globale")
        )
        log("Températures extrêmes:")
        temp_extremes.show()
        
        # Villes avec meilleure/pire qualité d'air
        air_quality = df_clean.groupBy("ville").agg(
            avg("aqi").alias("aqi_moyen")
        ).orderBy("aqi_moyen")
        
        log("Qualité d'air moyenne par ville (du meilleur au pire):")
        air_quality.show()
        
        # Alertes pollution
        high_pollution_cities = df_clean.filter(col("aqi") > 100).select("ville", "aqi").distinct()
        pollution_count = high_pollution_cities.count()
        
        if pollution_count > 0:
            log(f"⚠️ {pollution_count} ville(s) avec pollution élevée (AQI > 100):")
            high_pollution_cities.show()
        else:
            log("✅ Aucune pollution élevée détectée dans les données")
        
        # Sauvegarde des métriques de performance dans toutes les bases
        try:
            performance_metrics = spark.createDataFrame([
                (
                    datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "spark_load",
                    df_clean.count(),
                    len(df_clean.columns),
                    valid_count,
                    "success"
                )
            ], ["timestamp", "operation", "rows_processed", "columns", "valid_rows", "status"])
            
            log("📊 Métriques de performance générées")
            performance_metrics.show()
            
            # Optionnel : Sauvegarder les métriques dans les bases
            for db_name, db_url, db_props in [
                ("locale", db_url_local, db_properties_local),
                ("cloud", db_url_cloud, db_properties_cloud),
                ("vps", db_url_vps, db_properties_vps)
            ]:
                try:
                    performance_metrics.write \
                        .mode("append") \
                        .jdbc(db_url, "performance_metrics", properties=db_props)
                    log(f"📊 Métriques sauvegardées en base {db_name}")
                except Exception as e:
                    log(f"⚠️ Erreur sauvegarde métriques {db_name}: {e}")
            
        except Exception as e:
            log(f"⚠️ Erreur lors de la génération des métriques: {e}")
        
        # Optimisations mémoire
        df_clean.unpersist()  # Libération du cache
        
        log("🎉 Processus de chargement Spark terminé avec succès!")
        log(f"📊 Résumé : {df_clean.count()} lignes chargées dans 3 bases de données")
        
        return {
            "status": "success",
            "rows_processed": df_clean.count(),
            "valid_rows": valid_count,
            "environment": "docker" if is_docker else "local",
            "databases_loaded": ["local/docker", "cloud", "vps"]
        }
        
    except Exception as e:
        log(f"❌ Erreur fatale lors du chargement des données : {e}")
        log(f"📍 Environnement détecté : {'Docker' if os.path.exists('/opt/airflow') else 'Local'}")
        
        import traceback
        log("🔍 Trace complète de l'erreur:")
        log(traceback.format_exc())
        
        raise
    finally:
        spark.stop()
        log("🛑 Session Spark fermée")

def debug_environment_spark():
    """Fonction utilitaire pour déboguer l'environnement avec Spark"""
    log("🔍 === DEBUG ENVIRONNEMENT SPARK ===")
    log(f"📍 Répertoire courant : {os.getcwd()}")
    log(f"🐳 Docker détecté : {os.path.exists('/opt/airflow')}")
    log(f"🌍 Variables d'environnement Airflow : {'AIRFLOW_HOME' in os.environ}")
    
    # Test de session Spark
    try:
        spark = create_spark_session()
        log("✅ Session Spark créée avec succès")
        log(f"🔧 Version Spark : {spark.version}")
        log(f"🔧 Contexte Spark : {spark.sparkContext.appName}")
        spark.stop()
    except Exception as e:
        log(f"❌ Erreur lors de la création de session Spark : {e}")
    
    log(f"📁 Fichiers dans le répertoire courant :")
    try:
        for file in os.listdir('.'):
            log(f"   - {file}")
    except:
        log("   Impossible de lister les fichiers")
    
    if os.path.exists("/opt/airflow/project"):
        log(f"📁 Fichiers dans /opt/airflow/project :")
        try:
            for file in os.listdir('/opt/airflow/project'):
                log(f"   - {file}")
        except:
            log("   Impossible de lister les fichiers")

def test_databases_connectivity():
    """Test de connectivité vers toutes les bases de données"""
    log("🔍 === TEST DE CONNECTIVITÉ BASES DE DONNÉES ===")
    
    spark = create_spark_session()
    
    # Test de connectivité simple
    test_df = spark.createDataFrame([("test", 1)], ["name", "value"])
    
    databases = [
        ("Local/Docker", "jdbc:postgresql://localhost:15432/mspr3", {
            "user": "admin", "password": "admin123", "driver": "org.postgresql.Driver"
        }),
        ("Cloud", "jdbc:postgresql://ep-curly-bread-abg9804h-pooler.eu-west-2.aws.neon.tech:5432/mspr3", {
            "user": "mspr3_owner", "password": "npg_gIMFn84DuBpH", 
            "driver": "org.postgresql.Driver", "ssl": "true"
        }),
        ("VPS", "jdbc:postgresql://158.178.196.156:5432/mspr3", {
            "user": "postgres", "password": "admin123", "driver": "org.postgresql.Driver"
        })
    ]
    
    for db_name, db_url, db_props in databases:
        try:
            log(f"🔗 Test connexion {db_name}...")
            test_df.write \
                .mode("overwrite") \
                .jdbc(db_url, "connectivity_test", properties=db_props)
            log(f"✅ {db_name} : Connexion réussie")
        except Exception as e:
            log(f"❌ {db_name} : Échec - {e}")
    
    spark.stop()

def benchmark_spark_vs_pandas():
    """Compare les performances Spark vs Pandas pour le chargement"""
    log("🏁 === BENCHMARK SPARK VS PANDAS ===")
    
    import time
    
    # Test Spark
    start_time = time.time()
    try:
        result_spark = load_spark()
        spark_time = time.time() - start_time
        log(f"⏱️ Temps Spark : {spark_time:.2f} secondes")
    except Exception as e:
        log(f"❌ Erreur Spark : {e}")
        spark_time = None
    
    if spark_time:
        log(f"📊 Résultats Spark : {result_spark}")

if __name__ == "__main__":
    try:
        # Décommentez pour tester la connectivité
        test_databases_connectivity()
        
        # Décommentez la ligne suivante pour déboguer l'environnement
        debug_environment_spark()
        
        # Décommentez pour faire un benchmark
        benchmark_spark_vs_pandas()
        
        load_spark()
        
    except Exception as e:
        log(f"ERREUR FATALE: {str(e)}")
        sys.exit(1)