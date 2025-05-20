# retrieve_data_complete.py
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
        
        # Création de visualisations
        log("Création des visualisations")
        
        # 1. Graphique de comparaison des températures
        plt.figure(figsize=(14, 7))
        
        # Filtrer les données pour exclure les valeurs 'N/A'
        temp_data = df_complete.copy()
        temp_data = temp_data[temp_data['Température (°C)'] != 'N/A'].sort_values('Température (°C)', ascending=False)
        
        if not temp_data.empty:
            # Création du graphique à barres
            bars = plt.bar(temp_data['Ville'], temp_data['Température (°C)'], color='skyblue')
            
            # Ajouter les valeurs sur les barres
            for bar in bars:
                height = bar.get_height()
                plt.text(bar.get_x() + bar.get_width()/2., height + 0.2,
                        f'{height}°C', ha='center', va='bottom')
            
            plt.title('Comparaison des températures par ville', fontsize=16)
            plt.xlabel('Villes', fontsize=12)
            plt.ylabel('Température (°C)', fontsize=12)
            plt.xticks(rotation=45, ha='right')
            plt.tight_layout()
            
            # Sauvegarde du graphique
            os.makedirs('visualisations', exist_ok=True)
            temp_graph_path = "visualisations/temperature_comparison.png"
            plt.savefig(temp_graph_path)
            log(f"Graphique de température sauvegardé dans: {temp_graph_path}")
            plt.figure()  # Nouvelle figure pour le prochain graphique
        
        # 2. Graphique de comparaison des indices de qualité de l'air
        plt.figure(figsize=(14, 7))
        
        aqi_data = df_complete.copy()
        aqi_data = aqi_data[aqi_data['AQI'] != 'N/A'].sort_values('AQI', ascending=False)
        
        if not aqi_data.empty:
            # Définir une palette de couleurs basée sur les niveaux d'AQI
            aqi_values = aqi_data['AQI'].astype(float)
            
            # Créer un mappage de couleurs
            colors = []
            for aqi in aqi_values:
                if aqi <= 50:
                    colors.append('green')
                elif aqi <= 100:
                    colors.append('yellow')
                elif aqi <= 150:
                    colors.append('orange')
                elif aqi <= 200:
                    colors.append('red')
                elif aqi <= 300:
                    colors.append('purple')
                else:
                    colors.append('maroon')
            
            bars = plt.bar(aqi_data['Ville'], aqi_data['AQI'], color=colors)
            
            # Ajouter les valeurs sur les barres
            for bar in bars:
                height = bar.get_height()
                plt.text(bar.get_x() + bar.get_width()/2., height + 2,
                       f'{int(height)}', ha='center', va='bottom')
            
            plt.axhline(y=50, color='green', linestyle='--', alpha=0.5, label='Bon (0-50)')
            plt.axhline(y=100, color='yellow', linestyle='--', alpha=0.5, label='Modéré (51-100)')
            plt.axhline(y=150, color='orange', linestyle='--', alpha=0.5, label='Mauvais pour groupes sensibles (101-150)')
            plt.axhline(y=200, color='red', linestyle='--', alpha=0.5, label='Mauvais (151-200)')
            plt.axhline(y=300, color='purple', linestyle='--', alpha=0.5, label='Très mauvais (201-300)')
            
            plt.title('Qualité de l\'air (AQI) par ville', fontsize=16)
            plt.xlabel('Villes', fontsize=12)
            plt.ylabel('Indice de qualité de l\'air (AQI)', fontsize=12)
            plt.xticks(rotation=45, ha='right')
            plt.legend()
            plt.tight_layout()
            
            aqi_graph_path = "visualisations/aqi_comparison.png"
            plt.savefig(aqi_graph_path)
            log(f"Graphique d'AQI sauvegardé dans: {aqi_graph_path}")
            plt.figure()  # Nouvelle figure pour le prochain graphique
        
        # 3. Graphique de comparaison des polluants
        plt.figure(figsize=(14, 7))
        
        # Préparation des données pour le graphique des polluants
        pollutants_data = df_complete.copy()
        pollutants_data = pollutants_data[['Ville', 'PM2.5', 'PM10', 'O3', 'NO2']]
        
        # Convertir en valeurs numériques
        for col in ['PM2.5', 'PM10', 'O3', 'NO2']:
            pollutants_data[col] = pd.to_numeric(pollutants_data[col], errors='coerce')
        
        # Supprimer les lignes avec des valeurs NaN
        pollutants_data = pollutants_data.dropna()
        
        if not pollutants_data.empty:
            # Créer un graphique à barres groupées
            width = 0.2  # Largeur des barres
            x = np.arange(len(pollutants_data))
            
            plt.bar(x - 1.5*width, pollutants_data['PM2.5'], width, label='PM2.5', color='#1f77b4')
            plt.bar(x - 0.5*width, pollutants_data['PM10'], width, label='PM10', color='#ff7f0e')
            plt.bar(x + 0.5*width, pollutants_data['O3'], width, label='O3', color='#2ca02c')
            plt.bar(x + 1.5*width, pollutants_data['NO2'], width, label='NO2', color='#d62728')
            
            plt.title('Concentrations des polluants par ville', fontsize=16)
            plt.xlabel('Villes', fontsize=12)
            plt.ylabel('Concentration', fontsize=12)
            plt.xticks(x, pollutants_data['Ville'], rotation=45, ha='right')
            plt.legend()
            plt.tight_layout()
            
            pollutants_graph_path = "visualisations/pollutants_comparison.png"
            plt.savefig(pollutants_graph_path)
            log(f"Graphique des polluants sauvegardé dans: {pollutants_graph_path}")
        
        # Affichage interactif pour une ville spécifique
        print("\n" + "="*100)
        print("CONSULTATION DÉTAILLÉE PAR VILLE")
        print("="*100)
        
        # Créer un dictionnaire avec les données des villes pour faciliter l'accès
        city_dict = {city['Ville']: city for city in cities_data}
        
        # Option pour exporter les données en CSV
        export_option = input("Voulez-vous exporter toutes les données en CSV? (o/n): ")
        if export_option.lower() == 'o':
            csv_path = "donnees_completes.csv"
            df_complete.to_csv(csv_path, index=False)
            print(f"Données exportées dans: {csv_path}")
        
        while True:
            print("\nVilles disponibles: " + ", ".join(city_dict.keys()))
            city_input = input("\nEntrez le nom d'une ville pour voir les détails (ou 'q' pour quitter): ")
            
            if city_input.lower() == 'q':
                break
            
            if city_input in city_dict:
                city = city_dict[city_input]
                
                print("\n" + "="*100)
                print(f"RAPPORT DÉTAILLÉ POUR {city['Ville'].upper()}")
                print("="*100)
                
                # Informations de base
                print("\nINFORMATIONS DE BASE:")
                print(f"  Ville: {city['Ville']}")
                print(f"  Coordonnées: {city['Latitude']}, {city['Longitude']}")
                print(f"  Horodatage: {city['Timestamp']}")
                
                # Données météo
                print("\nDONNÉES MÉTÉOROLOGIQUES:")
                print(f"  Température: {city['Température (°C)']}°C ({city['Température (K)']} K)")
                print(f"  Température ressentie: {city['Température ressentie (°C)']}°C ({city['Température ressentie (K)']} K)")
                print(f"  Condition: {city['Condition météo']} - {city['Description météo']}")
                print(f"  Pression: {city['Pression (hPa)']} hPa")
                print(f"  Humidité: {city['Humidité (%)']}%")
                print(f"  Visibilité: {city['Visibilité (m)']} mètres")
                print(f"  Vent: {city['Vitesse du vent (m/s)']} m/s, direction: {city['Direction du vent (°)']}°")
                print(f"  Couverture nuageuse: {city['Couverture nuageuse (%)']}%")
                
                # Données de qualité d'air
                print("\nDONNÉES DE QUALITÉ D'AIR:")
                print(f"  Indice de qualité de l'air (AQI): {city['AQI']}")
                print(f"  Polluant dominant: {city['Polluant dominant']}")
                print(f"  Horodatage AQI: {city['Horodatage AQI']}")
                
                # Interprétation de l'AQI
                if city['AQI'] != 'N/A' and isinstance(city['AQI'], (int, float)):
                    aqi = city['AQI']
                    if aqi <= 50:
                        quality = "Bon"
                        impact = "Aucun impact sur la santé"
                    elif aqi <= 100:
                        quality = "Modéré"
                        impact = "Acceptable pour la plupart des gens"
                    elif aqi <= 150:
                        quality = "Mauvais pour les groupes sensibles"
                        impact = "Les personnes sensibles peuvent ressentir des effets"
                    elif aqi <= 200:
                        quality = "Mauvais"
                        impact = "Effets sur la santé pour tous"
                    elif aqi <= 300:
                        quality = "Très mauvais"
                        impact = "Avertissement sanitaire"
                    else:
                        quality = "Dangereux"
                        impact = "Alerte sanitaire"
                    
                    print(f"  Qualité: {quality}")
                    print(f"  Impact: {impact}")
                
                # Polluants
                print("\n  POLLUANTS:")
                print(f"    PM2.5: {city['PM2.5']}")
                print(f"    PM10: {city['PM10']}")
                print(f"    O3 (Ozone): {city['O3']}")
                print(f"    NO2 (Dioxyde d'azote): {city['NO2']}")
                
                print("="*100)
            else:
                print(f"Aucune donnée trouvée pour la ville: {city_input}")
        
        # Afficher les graphiques
        plt.show()
        
        log("Affichage des données terminé")
        
    except Exception as e:
        log(f"Erreur lors de la récupération des données: {str(e)}")
        import traceback
        log(traceback.format_exc())

if __name__ == "__main__":
    retrieve_and_display_complete()