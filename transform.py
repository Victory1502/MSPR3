# transform.py
import json
import pandas as pd
from minio import Minio
from io import BytesIO
from datetime import datetime
import sys
import os
from tabulate import tabulate
import matplotlib.pyplot as plt
from dateutil import parser
import numpy as np

def log(message):
    print(f"[INFO] {message}")
    sys.stdout.flush()

# ...existing code...

def retrieve_and_display_complete():
    log("Démarrage de la récupération des données complètes")
    
    # Configuration MinIO
    try:
        log("Connexion à MinIO sur localhost:9000")
        minio_client = Minio(
            "localhost:9000",
            access_key="minio",
            secret_key="minio123",
            secure=False
        )
        
        bucket_name = "goodair-raw"
        
        # Vérification de l'existence du bucket
        if not minio_client.bucket_exists(bucket_name):
            log(f"Le bucket {bucket_name} n'existe pas")
            return
        
        # Récupération de la liste des objets
        objects = list(minio_client.list_objects(bucket_name, recursive=True))
        log(f"Nombre d'objets trouvés: {len(objects)}")
        
        # Filtrer pour ne garder que les fichiers all_cities ou les fichiers individuels de villes
        city_files = [obj.object_name for obj in objects if "all_cities_" in obj.object_name or "_2025_" in obj.object_name]
        log(f"Nombre de fichiers potentiels trouvés: {len(city_files)}")
        
        if not city_files:
            log("Aucun fichier de données trouvé")
            return
        
        # Trier par date pour obtenir le plus récent
        city_files.sort(reverse=True)
        latest_file = city_files[0]
        log(f"Fichier le plus récent: {latest_file}")
        
        # Télécharger le contenu du fichier
        data = minio_client.get_object(bucket_name, latest_file)
        content = data.read().decode('utf-8')
        file_json = json.loads(content)
        
        # Déterminer si le fichier contient une liste de villes ou une seule ville
        if "villes" in file_json:
            city_data_list = file_json["villes"]
            timestamp = file_json.get("timestamp", "N/A")
        else:
            # Si c'est un fichier pour une seule ville
            city_data_list = [file_json]
            timestamp = file_json.get("timestamp_extraction", "N/A")
        
        log(f"Données récupérées pour {len(city_data_list)} villes")
        
        # Créer un DataFrame pandas avec toutes les colonnes demandées
        cities_data = []
        for city_data in city_data_list:
            # Informations de base
            data_row = {
                'Ville': city_data.get('ville', 'N/A'),
                'Latitude': city_data.get('latitude', 'N/A'),
                'Longitude': city_data.get('longitude', 'N/A'),
                'Timestamp': city_data.get('timestamp_extraction', 'N/A')
            }
            
            # Extraction des données météo
            meteo_info = city_data.get('meteo', {})
            
            # Température et données principales
            main_info = meteo_info.get('main', {})
            data_row['Température (K)'] = main_info.get('temp', 'N/A')
            data_row['Température (°C)'] = round(main_info.get('temp', 0) - 273.15, 1) if isinstance(main_info.get('temp'), (int, float)) else 'N/A'
            data_row['Température ressentie (K)'] = main_info.get('feels_like', 'N/A')
            data_row['Température ressentie (°C)'] = round(main_info.get('feels_like', 0) - 273.15, 1) if isinstance(main_info.get('feels_like'), (int, float)) else 'N/A'
            data_row['Pression (hPa)'] = main_info.get('pressure', 'N/A')
            data_row['Humidité (%)'] = main_info.get('humidity', 'N/A')
            
            # Conditions météo
            weather_info = meteo_info.get('weather', [{}])[0] if meteo_info.get('weather') else {}
            data_row['Condition météo'] = weather_info.get('main', 'N/A')
            data_row['Description météo'] = weather_info.get('description', 'N/A')
            
            # Autres données météo
            data_row['Visibilité (m)'] = meteo_info.get('visibility', 'N/A')
            
            wind_info = meteo_info.get('wind', {})
            data_row['Vitesse du vent (m/s)'] = wind_info.get('speed', 'N/A')
            data_row['Direction du vent (°)'] = wind_info.get('deg', 'N/A')
            
            clouds_info = meteo_info.get('clouds', {})
            data_row['Couverture nuageuse (%)'] = clouds_info.get('all', 'N/A')
            
            # Extraction des données de qualité d'air
            air_info = city_data.get('qualite_air', {})
            air_data = air_info.get('data', {})
            
            # Données AQI générales
            data_row['AQI'] = air_data.get('aqi', 'N/A')
            data_row['Polluant dominant'] = air_data.get('dominentpol', 'N/A')
            
            # Polluants spécifiques
            iaqi_data = air_data.get('iaqi', {})
            data_row['PM2.5'] = iaqi_data.get('pm25', {}).get('v', 'N/A') if isinstance(iaqi_data.get('pm25'), dict) else 'N/A'
            data_row['PM10'] = iaqi_data.get('pm10', {}).get('v', 'N/A') if isinstance(iaqi_data.get('pm10'), dict) else 'N/A'
            data_row['O3'] = iaqi_data.get('o3', {}).get('v', 'N/A') if isinstance(iaqi_data.get('o3'), dict) else 'N/A'
            data_row['NO2'] = iaqi_data.get('no2', {}).get('v', 'N/A') if isinstance(iaqi_data.get('no2'), dict) else 'N/A'
            
            # Horodatage des données de qualité d'air
            time_info = air_data.get('time', {})
            data_row['Horodatage AQI'] = time_info.get('iso', 'N/A')
            
            cities_data.append(data_row)
        
        # Créer un DataFrame complet
        df_complete = pd.DataFrame(cities_data)
        
        # Affichage des données par catégorie sous forme de tableau
        print("\n" + "="*100)
        print(f"DONNÉES COMPLÈTES - {timestamp}")
        print("="*100)
        
        # 1. Informations de base
        print("\nINFORMATIONS DE BASE:")
        print(tabulate(df_complete[['Ville', 'Latitude', 'Longitude', 'Timestamp']], 
                      headers='keys', tablefmt='pretty', showindex=False))
        
        # 2. Données météorologiques principales
        print("\nDONNÉES MÉTÉOROLOGIQUES PRINCIPALES:")
        meteo_columns = ['Ville', 'Température (°C)', 'Température ressentie (°C)', 
                        'Pression (hPa)', 'Humidité (%)', 'Condition météo', 'Description météo']
        print(tabulate(df_complete[meteo_columns], headers='keys', tablefmt='pretty', showindex=False))
        
        # 3. Données météorologiques supplémentaires
        print("\nDONNÉES MÉTÉOROLOGIQUES SUPPLÉMENTAIRES:")
        meteo_supp_columns = ['Ville', 'Visibilité (m)', 'Vitesse du vent (m/s)', 
                            'Direction du vent (°)', 'Couverture nuageuse (%)']
        print(tabulate(df_complete[meteo_supp_columns], headers='keys', tablefmt='pretty', showindex=False))
        
        # 4. Données de qualité d'air
        print("\nDONNÉES DE QUALITÉ D'AIR:")
        air_columns = ['Ville', 'AQI', 'Polluant dominant', 'PM2.5', 'PM10', 'O3', 'NO2', 'Horodatage AQI']
        print(tabulate(df_complete[air_columns], headers='keys', tablefmt='pretty', showindex=False))
        
        # Export CSV
        csv_path = "donnees_completes.csv"
        if os.path.exists(csv_path):
            # Charger l'existant et concaténer sans doublons exacts
            df_old = pd.read_csv(csv_path)
            df_concat = pd.concat([df_old, df_complete], ignore_index=True)
            # Supprimer les doublons exacts (toutes colonnes identiques)
            df_concat = df_concat.drop_duplicates()
            df_concat.to_csv(csv_path, index=False)
        else:
            df_complete.to_csv(csv_path, index=False)
        print(f"Données ajoutées dans: {csv_path}")
        
        print("\n" + "="*100)
        print("CONSULTATION DÉTAILLÉE PAR VILLE")
        print("="*100)
        
        # Créer un dictionnaire avec les données des villes pour faciliter l'accès
        city_dict = {city['Ville']: city for city in cities_data}
        
        log("Affichage des données terminé")
        
    except Exception as e:
        log(f"Erreur lors de la récupération des données: {str(e)}")
        import traceback
        log(traceback.format_exc())

if __name__ == "__main__":
    retrieve_and_display_complete()
