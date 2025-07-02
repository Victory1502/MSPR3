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

        # 📊 Chargement et traitement des données
        print(f"📖 Lecture du fichier CSV : {csv_file}")
        df = pd.read_csv(csv_file, encoding='utf-8-sig')
        
        print(f"📈 Données chargées : {len(df)} lignes, {len(df.columns)} colonnes")
        
        # Renommage des colonnes pour la base de données
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

        # 🌐 Connexions distantes - Configurations multiples à tester
        distant_configs = [
            {
                'name': 'VPS/Cloud (utilisateur admin)',
                'url': 'postgresql+psycopg2://admin:admin123@34.155.198.167:5432/mspr3'
            },
            {
                'name': 'VPS/Cloud (utilisateur postgres)',
                'url': 'postgresql+psycopg2://postgres:admin123@34.155.198.167:5432/mspr3'
            },
            {
                'name': 'VPS/Cloud (mot de passe alternatif)',
                'url': 'postgresql+psycopg2://postgres:password@34.155.198.167:5432/mspr3'
            }
        ]
        
        # Test de chaque configuration
        success = False
        for config in distant_configs:
            try:
                engine_distant = create_engine(config['url'])
                df.to_sql('meteo_air_quality', engine_distant, if_exists='append', index=False)
                print(f"✅ Données chargées dans {config['name']} avec succès.")
                success = True
                break  # Si ça marche, on s'arrête
            except Exception as e:
                print(f"⚠️ Échec {config['name']} : {str(e)[:100]}...")
        
        if not success:
            print("❌ Toutes les tentatives de connexion distante ont échoué.")
            print("💡 Vérifiez :")
            print("   - Les identifiants de connexion")
            print("   - L'accessibilité du serveur (firewall/VPN)")
            print("   - La configuration PostgreSQL")
            
        print("🎉 Processus de chargement terminé!")

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

def test_connection():
    """Tester uniquement la connexion à la base distante"""
    configs = [
        'postgresql+psycopg2://admin:admin123@158.178.196.156:5432/mspr3',
        'postgresql+psycopg2://postgres:admin123@158.178.196.156:5432/mspr3',
        'postgresql+psycopg2://admin:password@158.178.196.156:5432/mspr3'
    ]
    
    for i, config in enumerate(configs, 1):
        try:
            engine = create_engine(config)
            connection = engine.connect()
            connection.close()
            print(f"✅ Configuration {i} : Connexion réussie")
            return config
        except Exception as e:
            print(f"❌ Configuration {i} : {str(e)[:100]}...")
    
    return None

if __name__ == "__main__":
    # Décommentez pour tester uniquement la connexion
    # print("🔍 Test des connexions...")
    # test_connection()
    
    # Décommentez la ligne suivante pour déboguer l'environnement
    # debug_environment()
    
    load()