# retrieve_data.py
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

def log(message):
    print(f"[INFO] {message}")
    sys.stdout.flush()

def retrieve_and_display():
    log("Démarrage de la récupération des données")
    
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
        
        # Filtrer pour ne garder que les fichiers all_cities
        all_cities_files = [obj.object_name for obj in objects if "all_cities_" in obj.object_name]
        log(f"Nombre de fichiers all_cities trouvés: {len(all_cities_files)}")
        
        if not all_cities_files:
            log("Aucun fichier de données trouvé")
            return
        
        # Trier par date pour obtenir le plus récent
        all_cities_files.sort(reverse=True)
        latest_file = all_cities_files[0]
        log(f"Fichier le plus récent: {latest_file}")
        
        # Télécharger le contenu du fichier
        data = minio_client.get_object(bucket_name, latest_file)
        content = data.read().decode('utf-8')
        data_json = json.loads(content)
        
        log(f"Données récupérées pour {len(data_json['villes'])} villes")
        
        # Créer un DataFrame pandas pour affichage
        cities_data = []
        for city_data in data_json['villes']:
            ville = city_data['ville']
            timestamp = city_data['timestamp_extraction']
            
            # Extraction des données météo
            meteo_info = city_data['meteo']
            temperature = meteo_info.get('main', {}).get('temp', 'N/A')
            if temperature != 'N/A':
                temperature = round(temperature - 273.15, 1)  # Conversion Kelvin en Celsius
            
            weather_description = meteo_info.get('weather', [{}])[0].get('description', 'N/A')
            humidity = meteo_info.get('main', {}).get('humidity', 'N/A')
            wind_speed = meteo_info.get('wind', {}).get('speed', 'N/A')
            
            # Extraction des données de qualité d'air
            air_info = city_data['qualite_air']
            air_quality_index = air_info.get('data', {}).get('aqi', 'N/A')
            
            cities_data.append({
                'Ville': ville,
                'Température (°C)': temperature,
                'Description': weather_description,
                'Humidité (%)': humidity,
                'Vitesse du vent (m/s)': wind_speed,
                'Indice de qualité de l\'air': air_quality_index,
                'Horodatage': timestamp
            })
        
        # Créer un DataFrame
        df = pd.DataFrame(cities_data)
        
        # Affichage des données sous forme de tableau
        print("\n" + "="*80)
        print(f"DONNÉES MÉTÉO ET QUALITÉ DE L'AIR - {parser.parse(data_json['timestamp']).strftime('%d/%m/%Y à %H:%M:%S')}")
        print("="*80)
        print(tabulate(df[['Ville', 'Température (°C)', 'Description', 'Humidité (%)', 'Indice de qualité de l\'air']], 
                      headers='keys', tablefmt='pretty', showindex=False))
        print("="*80 + "\n")
        
        # Création d'un graphique
        log("Création d'un graphique de comparaison des températures")
        
        # Filtrer les données pour exclure les valeurs 'N/A'
        plot_data = df[df['Température (°C)'] != 'N/A'].sort_values('Température (°C)', ascending=False)
        
        plt.figure(figsize=(12, 6))
        bars = plt.bar(plot_data['Ville'], plot_data['Température (°C)'], color='skyblue')
        
        # Ajouter les valeurs sur les barres
        for bar in bars:
            height = bar.get_height()
            plt.text(bar.get_x() + bar.get_width()/2., height,
                    f'{height}°C', ha='center', va='bottom')
        
        plt.title('Comparaison des températures par ville', fontsize=14)
        plt.xlabel('Villes', fontsize=12)
        plt.ylabel('Température (°C)', fontsize=12)
        plt.xticks(rotation=45)
        plt.tight_layout()
        
        # Sauvegarde du graphique
        graph_path = "temperature_comparison.png"
        plt.savefig(graph_path)
        log(f"Graphique sauvegardé dans: {graph_path}")
        
        # Affichage du graphique
        plt.show()
        
        # Affichage détaillé pour une ville spécifique
        while True:
            city_input = input("\nEntrez le nom d'une ville pour voir les détails (ou 'q' pour quitter): ")
            
            if city_input.lower() == 'q':
                break
            
            city_data = next((c for c in data_json['villes'] if c['ville'].lower() == city_input.lower()), None)
            
            if city_data:
                print("\n" + "="*80)
                print(f"DÉTAILS POUR {city_data['ville'].upper()}")
                print("="*80)
                
                # Affichage des données météo
                meteo = city_data['meteo']
                print("\nDONNÉES MÉTÉO:")
                print(f"  Température: {round(meteo.get('main', {}).get('temp', 0) - 273.15, 1)}°C")
                print(f"  Ressenti: {round(meteo.get('main', {}).get('feels_like', 0) - 273.15, 1)}°C")
                print(f"  Pression: {meteo.get('main', {}).get('pressure', 'N/A')} hPa")
                print(f"  Humidité: {meteo.get('main', {}).get('humidity', 'N/A')}%")
                print(f"  Visibilité: {meteo.get('visibility', 'N/A')} mètres")
                print(f"  Vent: {meteo.get('wind', {}).get('speed', 'N/A')} m/s, direction: {meteo.get('wind', {}).get('deg', 'N/A')}°")
                print(f"  Conditions: {meteo.get('weather', [{}])[0].get('main', 'N/A')} - {meteo.get('weather', [{}])[0].get('description', 'N/A')}")
                
                # Affichage des données de qualité d'air
                air = city_data['qualite_air']
                print("\nQUALITÉ DE L'AIR:")
                
                if isinstance(air.get('data'), dict):
                    aqi = air.get('data', {}).get('aqi', 'N/A')
                    print(f"  Indice de qualité de l'air (AQI): {aqi}")
                    
                    # Interprétation de l'indice AQI
                    if isinstance(aqi, int):
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
                    
                    # Afficher les polluants si disponibles
                    iaqi = air.get('data', {}).get('iaqi', {})
                    if iaqi:
                        print("\n  POLLUANTS:")
                        for pollutant, value in iaqi.items():
                            if isinstance(value, dict) and 'v' in value:
                                print(f"    {pollutant}: {value['v']}")
                else:
                    print("  Données de qualité d'air non disponibles ou format incorrect")
                
                print("="*80)
            else:
                print(f"Aucune donnée trouvée pour la ville: {city_input}")
        
        log("Affichage des données terminé")
        
    except Exception as e:
        log(f"Erreur lors de la récupération des données: {str(e)}")
        import traceback
        log(traceback.format_exc())

if __name__ == "__main__":
    retrieve_and_display()