import json
import requests
import traceback
from datetime import datetime
from typing import List, Dict, Tuple, Optional
import time
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from minio import Minio
from minio.error import S3Error
from io import BytesIO

# Configuration du logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def log(message: str):
    """Fonction de logging unifiée"""
    logger.info(message)
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] {message}")

class WeatherDataExtractor:
    """Extracteur de données météo et qualité de l'air optimisé"""
    
    def __init__(self, 
                 weather_api_key: str = "80f2502929bbdbaf3072277eb280a83f",
                 air_quality_token: str = "ca9559f64030829280e1efe135d52fab54ca3d6e",
                 minio_endpoint: str = "localhost:9000",
                 minio_access_key: str = "minioadmin",
                 minio_secret_key: str = "minioadmin",
                 bucket_name: str = "weather-data",
                 use_secure: bool = False):
        
        self.weather_api_key = weather_api_key
        self.air_quality_token = air_quality_token
        self.bucket_name = bucket_name
        
        # Initialisation du client MinIO (optionnel)
        try:
            self._initialize_minio(minio_endpoint, minio_access_key, minio_secret_key, use_secure)
        except Exception as e:
            log(f"MinIO non disponible, fonctionnement sans sauvegarde: {str(e)}")
            self.minio_client = None
    
    def _initialize_minio(self, endpoint: str, access_key: str, secret_key: str, secure: bool):
        """Initialiser le client MinIO"""
        try:
            self.minio_client = Minio(
                endpoint,
                access_key=access_key,
                secret_key=secret_key,
                secure=secure
            )
            
            # Créer le bucket s'il n'existe pas
            if not self.minio_client.bucket_exists(self.bucket_name):
                self.minio_client.make_bucket(self.bucket_name)
                log(f"Bucket '{self.bucket_name}' créé avec succès")
            else:
                log(f"Bucket '{self.bucket_name}' existe déjà")
                
        except Exception as e:
            log(f"Erreur d'initialisation MinIO: {str(e)}")
            self.minio_client = None
            # Ne pas lever l'exception, permettre de continuer sans MinIO
    
    def fetch_weather_data(self, latitude: float, longitude: float) -> Dict:
        """Récupérer les données météo"""
        try:
            url = f"https://api.openweathermap.org/data/2.5/weather?lat={latitude}&lon={longitude}&appid={self.weather_api_key}&units=metric&lang=fr"
            response = requests.get(url, timeout=15)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            log(f"Erreur météo: {str(e)}")
            return None
    
    def fetch_air_quality_data(self, latitude: float, longitude: float) -> Dict:
        """Récupérer les données de qualité de l'air"""
        try:
            url = f"https://api.waqi.info/feed/geo:{latitude};{longitude}/?token={self.air_quality_token}"
            response = requests.get(url, timeout=15)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            log(f"Erreur qualité air: {str(e)}")
            return None
    
    def fetch_city_data(self, ville: str, latitude: float, longitude: float, max_retries: int = 3) -> Dict:
        """Récupérer toutes les données pour une ville avec retry logic"""
        retry_delay = 1
        
        for attempt in range(max_retries):
            try:
                log(f"Collecte {ville} (tentative {attempt + 1}/{max_retries})")
                
                weather_data = self.fetch_weather_data(latitude, longitude)
                air_quality_data = self.fetch_air_quality_data(latitude, longitude)
                
                result = {
                    "ville": ville,
                    "latitude": latitude,
                    "longitude": longitude,
                    "meteo": weather_data,
                    "qualite_air": air_quality_data,
                    "timestamp_extraction": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "status": "success" if (weather_data and air_quality_data) else "partial" if (weather_data or air_quality_data) else "failed"
                }
                
                if result["status"] == "success":
                    log(f"✅ {ville} - Données complètes collectées")
                elif result["status"] == "partial":
                    log(f"⚠️  {ville} - Données partielles collectées")
                else:
                    log(f"❌ {ville} - Échec de collecte")
                
                return result
                
            except Exception as e:
                log(f"Erreur {ville} (tentative {attempt + 1}): {str(e)}")
                
                if attempt < max_retries - 1:
                    time.sleep(retry_delay * (attempt + 1))
                else:
                    return {
                        "ville": ville,
                        "latitude": latitude,
                        "longitude": longitude,
                        "meteo": None,
                        "qualite_air": None,
                        "timestamp_extraction": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                        "status": "failed",
                        "error": str(e)
                    }
    
    def save_to_minio(self, data: Dict, filename: str = None) -> bool:
        """Sauvegarder les données dans MinIO"""
        if not self.minio_client:
            log(f"MinIO non disponible - Données {data.get('ville', 'unknown')}: {data.get('status', 'unknown')}")
            return False
        
        try:
            if not filename:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                filename = f"weather_data_{data.get('ville', 'unknown')}_{timestamp}.json"
            
            json_data = json.dumps(data, indent=2, ensure_ascii=False)
            json_bytes = json_data.encode('utf-8')
            
            self.minio_client.put_object(
                self.bucket_name,
                filename,
                data=BytesIO(json_bytes),
                length=len(json_bytes),
                content_type='application/json; charset=utf-8'
            )
            
            log(f"💾 Sauvegardé: {filename}")
            return True
            
        except S3Error as e:
            log(f"❌ Erreur MinIO: {str(e)}")
            return False
        except Exception as e:
            log(f"❌ Erreur sauvegarde: {str(e)}")
            return False
    
    def save_batch_to_minio(self, data_list: List[Dict], filename: str = None) -> bool:
        """Sauvegarder un lot de données dans MinIO"""
        if not filename:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"weather_data_batch_{timestamp}.json"
        
        successful = len([d for d in data_list if d.get('status') == 'success'])
        partial = len([d for d in data_list if d.get('status') == 'partial'])
        failed = len([d for d in data_list if d.get('status') == 'failed'])
        
        batch_data = {
            "extraction_info": {
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "total_cities": len(data_list),
                "successful_extractions": successful,
                "partial_extractions": partial,
                "failed_extractions": failed,
                "success_rate": f"{(successful / len(data_list) * 100):.1f}%"
            },
            "data": data_list
        }
        
        return self.save_to_minio(batch_data, filename)
    
    def extract_single_city(self, ville: str, latitude: float, longitude: float, save_individual: bool = True) -> Dict:
        """Extraire les données pour une seule ville"""
        result = self.fetch_city_data(ville, latitude, longitude)
        
        if save_individual:
            self.save_to_minio(result)
        
        return result
    
    def extract_multiple_cities_sequential(self, cities_data: List[Tuple[str, float, float]], 
                                         save_individual: bool = True, 
                                         save_batch: bool = True) -> List[Dict]:
        """Extraction séquentielle (méthode recommandée)"""
        log(f"🚀 Extraction séquentielle pour {len(cities_data)} villes")
        
        all_results = []
        
        for i, (ville, latitude, longitude) in enumerate(cities_data, 1):
            log(f"[{i}/{len(cities_data)}] Traitement de {ville}")
            result = self.extract_single_city(ville, latitude, longitude, save_individual)
            all_results.append(result)
        
        if save_batch:
            self.save_batch_to_minio(all_results)
        
        # Statistiques finales
        successful = len([r for r in all_results if r['status'] == 'success'])
        partial = len([r for r in all_results if r['status'] == 'partial'])
        failed = len([r for r in all_results if r['status'] == 'failed'])
        
        log(f"📊 Résultats: {successful} succès, {partial} partiels, {failed} échecs sur {len(cities_data)} villes")
        
        return all_results
    
    def extract_multiple_cities_parallel(self, cities_data: List[Tuple[str, float, float]], 
                                       max_workers: int = 4,
                                       save_individual: bool = True, 
                                       save_batch: bool = True) -> List[Dict]:
        """Extraction parallèle avec ThreadPoolExecutor"""
        log(f"🚀 Extraction parallèle pour {len(cities_data)} villes (workers: {max_workers})")
        
        all_results = []
        
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            # Soumettre toutes les tâches
            future_to_city = {
                executor.submit(self.fetch_city_data, ville, lat, lon): ville
                for ville, lat, lon in cities_data
            }
            
            # Traiter les résultats au fur et à mesure
            for future in as_completed(future_to_city):
                ville = future_to_city[future]
                try:
                    result = future.result()
                    all_results.append(result)
                    
                    if save_individual:
                        self.save_to_minio(result)
                        
                except Exception as e:
                    log(f"❌ Exception pour {ville}: {str(e)}")
                    error_result = {
                        "ville": ville,
                        "status": "failed",
                        "error": str(e),
                        "timestamp_extraction": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    }
                    all_results.append(error_result)
        
        if save_batch:
            self.save_batch_to_minio(all_results)
        
        # Statistiques finales
        successful = len([r for r in all_results if r['status'] == 'success'])
        partial = len([r for r in all_results if r['status'] == 'partial'])
        failed = len([r for r in all_results if r['status'] == 'failed'])
        
        log(f"📊 Résultats parallèles: {successful} succès, {partial} partiels, {failed} échecs sur {len(cities_data)} villes")
        
        return all_results
    
    def test_apis(self) -> bool:
        """Tester les APIs avec Paris"""
        log("🧪 Test des APIs avec Paris...")
        
        try:
            result = self.extract_single_city("Paris", 48.8566, 2.3522, save_individual=False)
            success = result.get('status') == 'success'
            log(f"Test APIs: {'✅ Réussi' if success else '❌ Échoué'}")
            return success
        except Exception as e:
            log(f"❌ Erreur test APIs: {str(e)}")
            return False

def create_cities_list() -> List[Tuple[str, float, float]]:
    """Liste des villes françaises avec coordonnées"""
    return [
        ("Paris", 48.8566, 2.3522),
        ("Marseille", 43.2965, 5.3698),
        ("Lyon", 45.7640, 4.8357),
        ("Toulouse", 43.6047, 1.4442),
        ("Nice", 43.7102, 7.2620),
        ("Nantes", 47.2184, -1.5536),
        ("Montpellier", 43.6110, 3.8767),
        ("Strasbourg", 48.5734, 7.7521),
        ("Bordeaux", 44.8378, -0.5792),
        ("Lille", 50.6292, 3.0573),
        ("Rennes", 48.1173, -1.6778),
        ("Reims", 49.2583, 4.0317),
        ("Saint-Étienne", 45.4397, 4.3872),
        ("Le Havre", 49.4944, 0.1079),
        ("Toulon", 43.1242, 5.9280)
    ]

def main():
    """Fonction principale optimisée"""
    log("=" * 60)
    log("🌤️  EXTRACTEUR DE DONNÉES MÉTÉO OPTIMISÉ")
    log("=" * 60)
    
    # Initialisation
    extractor = WeatherDataExtractor()
    cities = create_cities_list()
    
    # Test des APIs
    if not extractor.test_apis():
        log("❌ APIs non fonctionnelles - Arrêt du programme")
        return
    
    log("✅ APIs fonctionnelles - Début de l'extraction")
    
    # Menu de choix
    print("\n📋 Méthodes d'extraction disponibles:")
    print("1. Séquentielle (recommandée, stable)")
    print("2. Parallèle (plus rapide)")
    print("3. Test sur 3 villes seulement")
    
    choice = input("\nChoisissez une méthode (1-3): ").strip()
    
    if choice == "3":
        cities = cities[:3]
        log(f"🧪 Mode test avec {len(cities)} villes")
    
    if choice == "2":
        log("\n🔄 Extraction parallèle")
        results = extractor.extract_multiple_cities_parallel(cities, max_workers=4)
    else:
        log("\n🔄 Extraction séquentielle")
        results = extractor.extract_multiple_cities_sequential(cities)
    
    # Résumé final
    successful = len([r for r in results if r['status'] == 'success'])
    total = len(results)
    success_rate = (successful / total * 100) if total > 0 else 0
    
    log("=" * 60)
    log(f"🎯 EXTRACTION TERMINÉE")
    log(f"📈 Taux de réussite: {success_rate:.1f}% ({successful}/{total})")
    log("=" * 60)

if __name__ == "__main__":
    main()