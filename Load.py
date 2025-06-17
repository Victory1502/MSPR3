import pandas as pd
import os
from sqlalchemy import create_engine

def load():
    try:
        # 🔧 Détection automatique de l'environnement et chemins adaptatifs
        csv_paths = [
            "donnees_completes.csv",  # Chemin local (répertoire courant)
            "/opt/airflow/project/donnees_completes.csv",  # Chemin Docker principal
            "/opt/airflow/donnees_completes.csv",  # Chemin Docker alternatif
            "/opt/airflow/dags/donnees_completes.csv",  # Chemin Docker dans dags
            "./project/donnees_completes.csv",  # Chemin relatif projet
            os.path.join(os.getcwd(), "donnees_completes.csv"),  # Chemin absolu local
        ]
        
        csv_file = None
        for path in csv_paths:
            if os.path.exists(path):
                csv_file = path
                print(f"✅ Fichier CSV trouvé à : {csv_file}")
                break
        
        if csv_file is None:
            # Affichage des chemins testés pour debug
            print("❌ Fichier 'donnees_completes.csv' introuvable.")
            print("📂 Chemins testés :")
            for i, path in enumerate(csv_paths, 1):
                print(f"   {i}. {path}")
            print(f"📍 Répertoire de travail actuel : {os.getcwd()}")
            print(f"📁 Contenu du répertoire courant : {os.listdir('.')}")
            
            # Si on est dans Docker, afficher aussi le contenu du projet
            if os.path.exists("/opt/airflow/project"):
                print(f"📁 Contenu de /opt/airflow/project : {os.listdir('/opt/airflow/project')}")
            
            raise FileNotFoundError("Fichier 'donnees_completes.csv' introuvable dans tous les emplacements testés.")

        # 🔧 Détection de l'environnement pour les connexions DB
        is_docker = os.path.exists("/opt/airflow") or "AIRFLOW_HOME" in os.environ
        
        if is_docker:
            # Configuration Docker - utilise le nom du service
            print("🐳 Environnement Docker détecté")
            engine = create_engine('postgresql+psycopg2://admin:admin123@postgres:5432/mspr3')
        else:
            # Configuration locale - utilise localhost avec le port mappé
            print("💻 Environnement local détecté")
            engine = create_engine('postgresql+psycopg2://admin:admin123@localhost:15432/mspr3')

        # 🌐 Connexion cloud (identique dans les deux environnements)
        engine_cloud = create_engine('postgresql://mspr3_owner:npg_gIMFn84DuBpH@ep-curly-bread-abg9804h-pooler.eu-west-2.aws.neon.tech/mspr3?sslmode=require')

        # 📊 Chargement et traitement des données
        print(f"📖 Lecture du fichier CSV : {csv_file}")
        df = pd.read_csv(csv_file, encoding='utf-8-sig')
        
        print(f"📈 Données chargées : {len(df)} lignes, {len(df.columns)} colonnes")
        
        df.columns = [
            'ville', 'latitude', 'longitude', 'timestamp_meteo',
            'temperature_k', 'temperature_c', 'temperature_ressentie_k', 'temperature_ressentie_c',
            'pression', 'humidite', 'condition_meteo', 'description_meteo',
            'visibilite', 'vitesse_vent', 'direction_vent', 'couverture_nuageuse',
            'aqi', 'polluant_dominant', 'pm25', 'pm10', 'o3', 'no2', 'horodatage_aqi'
        ]

        # 💾 Sauvegarde en base locale/docker
        try:
            df.to_sql('meteo_air_quality', engine, if_exists='append', index=False)
            env_type = "Docker" if is_docker else "local"
            print(f"✅ Données chargées dans la base {env_type} avec succès.")
        except Exception as e:
            print(f"⚠️ Erreur lors du chargement en base locale/docker : {e}")

        # 🌐 Sauvegarde en base cloud
        try:
            df.to_sql('meteo_air_quality', engine_cloud, if_exists='append', index=False)
            print("✅ Données chargées dans la base cloud avec succès.")
        except Exception as e:
            print(f"⚠️ Erreur lors du chargement en base cloud : {e}")
            
        print("🎉 Processus de chargement terminé avec succès!")

    except Exception as e:
        print(f"❌ Erreur fatale lors du chargement des données : {e}")
        print(f"📍 Environnement détecté : {'Docker' if os.path.exists('/opt/airflow') else 'Local'}")
        raise

def debug_environment():
    """Fonction utilitaire pour déboguer l'environnement"""
    print("🔍 === DEBUG ENVIRONNEMENT ===")
    print(f"📍 Répertoire courant : {os.getcwd()}")
    print(f"🐳 Docker détecté : {os.path.exists('/opt/airflow')}")
    print(f"🌍 Variables d'environnement Airflow : {'AIRFLOW_HOME' in os.environ}")
    print(f"📁 Fichiers dans le répertoire courant :")
    try:
        for file in os.listdir('.'):
            print(f"   - {file}")
    except:
        print("   Impossible de lister les fichiers")
    
    if os.path.exists("/opt/airflow/project"):
        print(f"📁 Fichiers dans /opt/airflow/project :")
        try:
            for file in os.listdir('/opt/airflow/project'):
                print(f"   - {file}")
        except:
            print("   Impossible de lister les fichiers")

if __name__ == "__main__":
    # Décommentez la ligne suivante pour déboguer l'environnement
    # debug_environment()
    load()