# spark_diagnostic.py - Diagnostic et solutions alternatives
import sys
import os
import subprocess
from pathlib import Path

def log(message):
    print(f"[DIAGNOSTIC] {message}")

def check_environment():
    """Diagnostic de l'environnement Spark/Python"""
    log("=== DIAGNOSTIC ENVIRONNEMENT ===")
    
    # Vérification Python
    log(f"Python version: {sys.version}")
    log(f"Python executable: {sys.executable}")
    
    # Vérification variables d'environnement
    java_home = os.environ.get('JAVA_HOME')
    spark_home = os.environ.get('SPARK_HOME')
    python_path = os.environ.get('PYTHONPATH')
    
    log(f"JAVA_HOME: {java_home}")
    log(f"SPARK_HOME: {spark_home}")
    log(f"PYTHONPATH: {python_path}")
    
    # Vérification modules Python
    try:
        import pyspark
        log(f"PySpark version: {pyspark.__version__}")
        log(f"PySpark path: {pyspark.__file__}")
    except ImportError as e:
        log(f"ERREUR PySpark: {e}")
        return False
    
    # Vérification Java
    try:
        result = subprocess.run(['java', '-version'], 
                              capture_output=True, text=True, timeout=10)
        log(f"Java disponible: {result.stderr.split()[2] if result.stderr else 'Non détecté'}")
    except Exception as e:
        log(f"ERREUR Java: {e}")
        return False
    
    return True

def fix_environment_variables():
    """Configuration automatique des variables d'environnement"""
    log("=== CORRECTION VARIABLES D'ENVIRONNEMENT ===")
    
    # Détection automatique JAVA_HOME
    if not os.environ.get('JAVA_HOME'):
        java_paths = [
            "C:\\Program Files\\Java\\jdk*",
            "C:\\Program Files\\OpenJDK\\jdk*",
            "C:\\Program Files (x86)\\Java\\jdk*"
        ]
        
        import glob
        for pattern in java_paths:
            matches = glob.glob(pattern)
            if matches:
                java_home = matches[0]
                os.environ['JAVA_HOME'] = java_home
                log(f"JAVA_HOME configuré: {java_home}")
                break
    
    # Configuration SPARK_HOME si détecté
    spark_paths = [
        "C:\\spark*",
        os.path.expanduser("~/spark*"),
        "./spark*"
    ]
    
    import glob
    for pattern in spark_paths:
        matches = glob.glob(pattern)
        if matches:
            spark_home = matches[0]
            os.environ['SPARK_HOME'] = spark_home
            log(f"SPARK_HOME configuré: {spark_home}")
            break

def create_spark_standalone():
    """Création Spark en mode standalone sans workers externes"""
    from pyspark.sql import SparkSession
    
    try:
        # Configuration ultra-simple
        spark = SparkSession.builder \
            .appName("DiagnosticTest") \
            .master("local[1]") \
            .config("spark.driver.host", "localhost") \
            .config("spark.driver.bindAddress", "127.0.0.1") \
            .config("spark.ui.enabled", "false") \
            .config("spark.sql.adaptive.enabled", "false") \
            .config("spark.serializer", "org.apache.spark.serializer.JavaSerializer") \
            .getOrCreate()
        
        # Test simple
        test_data = [("test", 1)]
        df = spark.createDataFrame(test_data, ["col1", "col2"])
        
        # Test de collection sans workers complexes
        result = df.take(1)
        log(f"Test réussi: {result}")
        
        spark.stop()
        return True
        
    except Exception as e:
        log(f"Erreur test standalone: {e}")
        return False

def alternative_pandas_processing():
    """Alternative complète avec Pandas au lieu de Spark"""
    log("=== ALTERNATIVE PANDAS ===")
    
    try:
        import pandas as pd
        import requests
        import json
        from datetime import datetime
        from minio import Minio
        from io import BytesIO
        
        # Données des villes
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
        
        # Création DataFrame Pandas
        df = pd.DataFrame(villes_data, columns=['ville', 'latitude', 'longitude'])
        log(f"DataFrame Pandas créé avec {len(df)} villes")
        
        # Simulation d'ajout de données API
        def fetch_api_simulation(row):
            return {
                'temperature': 15.5,
                'air_quality': 85,
                'timestamp': datetime.now().isoformat()
            }
        
        # Application de la fonction
        df['api_data'] = df.apply(fetch_api_simulation, axis=1)
        
        # Sauvegarde locale Parquet avec Pandas
        output_file = f"pandas_output_{datetime.now().strftime('%Y%m%d_%H%M%S')}.parquet"
        df.to_parquet(output_file, engine='pyarrow')
        log(f"Données sauvegardées en Parquet: {output_file}")
        
        # Sauvegarde JSON
        json_file = f"pandas_output_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        df.to_json(json_file, orient='records', indent=2)
        log(f"Données sauvegardées en JSON: {json_file}")
        
        return True
        
    except Exception as e:
        log(f"Erreur alternative Pandas: {e}")
        return False

def fix_spark_worker_issues():
    """Solutions spécifiques aux problèmes de workers Spark"""
    log("=== CORRECTIONS WORKERS SPARK ===")
    
    # Solution 1: Nettoyage des processus Spark existants
    try:
        if os.name == 'nt':  # Windows
            subprocess.run(['taskkill', '/F', '/IM', 'java.exe'], 
                         capture_output=True, timeout=10)
            log("Processus Java nettoyés (Windows)")
        else:  # Linux/Mac
            subprocess.run(['pkill', '-f', 'spark'], 
                         capture_output=True, timeout=10)
            log("Processus Spark nettoyés (Unix)")
    except Exception as e:
        log(f"Nettoyage processus: {e}")
    
    # Solution 2: Nettoyage des répertoires temporaires
    temp_dirs = [
        os.path.expanduser("~/tmp"),
        "./tmp",
        "/tmp/spark*" if os.name != 'nt' else None
    ]
    
    for temp_dir in temp_dirs:
        if temp_dir and Path(temp_dir).exists():
            try:
                import shutil
                shutil.rmtree(temp_dir, ignore_errors=True)
                log(f"Répertoire temporaire nettoyé: {temp_dir}")
            except Exception as e:
                log(f"Erreur nettoyage {temp_dir}: {e}")
    
    # Solution 3: Configuration réseau Windows
    if os.name == 'nt':
        log("Configuration réseau Windows détectée")
        log("RECOMMANDATION: Vérifiez que localhost résout vers 127.0.0.1")
        log("Commande: ping localhost")

def main():
    """Fonction principale de diagnostic"""
    log("DEBUT DIAGNOSTIC SPARK")
    
    # Étape 1: Vérification environnement
    if not check_environment():
        log("ECHEC: Environnement non configuré correctement")
        fix_environment_variables()
    
    # Étape 2: Test Spark minimal
    log("\nTest Spark minimal...")
    if create_spark_standalone():
        log("SUCCES: Spark fonctionne en mode minimal")
    else:
        log("ECHEC: Problèmes Spark détectés")
        fix_spark_worker_issues()
    
    # Étape 3: Alternative Pandas
    log("\nTest alternative Pandas...")
    if alternative_pandas_processing():
        log("SUCCES: Alternative Pandas disponible")
    else:
        log("ECHEC: Problèmes avec Pandas également")
    
    # Recommandations finales
    log("\n=== RECOMMANDATIONS ===")
    log("1. Utilisez le script extract_spark_optimized.py")
    log("2. Si échec persistant, utilisez l'alternative Pandas")
    log("3. Vérifiez votre configuration Java/Python")
    log("4. Redémarrez votre terminal après configuration")

if __name__ == "__main__":
    main()