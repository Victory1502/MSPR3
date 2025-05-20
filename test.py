# display_columns_by_level.py
import json
from minio import Minio
import sys
from collections import defaultdict

def log(message):
    print(f"[INFO] {message}")
    sys.stdout.flush()

def display_columns_by_level():
    log("Démarrage de l'analyse des colonnes par niveau")
    
    # Configuration MinIO
    try:
        log("Connexion à MinIO sur localhost:9000")
        minio_client = Minio(
            "localhost:9000",
            access_key="minio",
            secret_key="minio123",
            secure=False
        )
        
        # Vérifier dans les deux buckets possibles
        buckets_to_check = ["goodair-raw", "meteo-villes"]
        bucket_name = None
        
        for bucket in buckets_to_check:
            if minio_client.bucket_exists(bucket):
                bucket_name = bucket
                log(f"Bucket trouvé: {bucket_name}")
                break
        
        if not bucket_name:
            log("Aucun bucket valide trouvé")
            return
        
        # Récupération de la liste des objets
        objects = list(minio_client.list_objects(bucket_name, recursive=True))
        
        if not objects:
            log("Aucun fichier trouvé dans le bucket")
            return
        
        # Récupérer un fichier JSON qui contient des données météo
        json_files = [obj.object_name for obj in objects if obj.object_name.endswith(".json")]
        
        if not json_files:
            log("Aucun fichier JSON trouvé")
            return
        
        # Prendre le premier fichier disponible
        sample_file = json_files[0]
        log(f"Analyse du fichier: {sample_file}")
        
        # Télécharger le contenu du fichier
        data = minio_client.get_object(bucket_name, sample_file)
        content = data.read().decode('utf-8')
        data_json = json.loads(content)
        
        # Fonction pour extraire les chemins complets de tous les champs
        def extract_field_paths(obj, prefix="", result=None):
            if result is None:
                result = []
                
            if isinstance(obj, dict):
                for key, value in obj.items():
                    current_path = f"{prefix}.{key}" if prefix else key
                    result.append(current_path)
                    
                    if isinstance(value, (dict, list)):
                        extract_field_paths(value, current_path, result)
            
            elif isinstance(obj, list) and len(obj) > 0:
                # Pour les listes, examiner le premier élément comme exemple
                sample_item = obj[0]
                if isinstance(sample_item, (dict, list)):
                    extract_field_paths(sample_item, prefix, result)
                else:
                    # Si la liste contient des valeurs simples, ajouter [item] au chemin
                    current_path = f"{prefix}[item]"
                    if current_path not in result:
                        result.append(current_path)
            
            return result
        
        # Extraire tous les chemins de champs
        all_field_paths = extract_field_paths(data_json)
        
        # Organiser les champs par niveau de profondeur
        fields_by_depth = defaultdict(list)
        
        for path in all_field_paths:
            depth = path.count(".")
            fields_by_depth[depth].append(path)
        
        # Si on a un fichier qui contient une liste de villes, analyser une ville spécifique
        city_data = None
        if "villes" in data_json and isinstance(data_json["villes"], list) and len(data_json["villes"]) > 0:
            city_data = data_json["villes"][0]
            log(f"Analyse approfondie pour la ville: {city_data.get('ville', 'Inconnue')}")
            
            # Extraire tous les chemins pour une ville
            city_field_paths = extract_field_paths(city_data)
            
            # Organiser les champs par niveau pour la ville
            city_fields_by_depth = defaultdict(list)
            
            for path in city_field_paths:
                depth = path.count(".")
                city_fields_by_depth[depth].append(path)
        
        # Afficher les résultats
        print("\n" + "="*100)
        print("ANALYSE DÉTAILLÉE DES COLONNES PAR NIVEAU D'IMBRICATION")
        print("="*100)
        
        # Afficher les colonnes pour le fichier complet
        print("\n[STRUCTURE COMPLÈTE DU FICHIER]")
        
        max_depth = max(fields_by_depth.keys())
        
        for depth in range(max_depth + 1):
            fields = sorted(fields_by_depth[depth])
            print(f"\nNIVEAU {depth}:")
            print("-" * 40)
            
            for field in fields:
                # Ajouter une visualisation de la hiérarchie
                indent = "  " * depth
                field_name = field.split(".")[-1] if "." in field else field
                print(f"{indent}└─ {field_name}")
                
                # Pour le niveau 0, afficher aussi le type de donnée
                if depth == 0 and field in data_json:
                    value = data_json[field]
                    if isinstance(value, dict):
                        print(f"{indent}   └─ (Objet avec {len(value)} propriétés)")
                    elif isinstance(value, list):
                        print(f"{indent}   └─ (Liste avec {len(value)} éléments)")
                    else:
                        print(f"{indent}   └─ ({type(value).__name__})")
        
        # Si on a des données de ville, afficher leur structure
        if city_data:
            print("\n" + "="*100)
            print(f"STRUCTURE DÉTAILLÉE POUR UNE VILLE ({city_data.get('ville', 'Inconnue')})")
            print("="*100)
            
            max_city_depth = max(city_fields_by_depth.keys()) if city_fields_by_depth else 0
            
            for depth in range(max_city_depth + 1):
                fields = sorted(city_fields_by_depth[depth])
                print(f"\nNIVEAU {depth}:")
                print("-" * 40)
                
                for field in fields:
                    # Ajouter une visualisation de la hiérarchie
                    indent = "  " * depth
                    field_name = field.split(".")[-1] if "." in field else field
                    print(f"{indent}└─ {field_name}")
                    
                    # Pour les principaux objets, afficher plus de détails
                    if field in ["meteo", "qualite_air"]:
                        value = city_data[field]
                        if isinstance(value, dict):
                            print(f"{indent}   └─ (Objet avec {len(value)} propriétés)")
                        elif isinstance(value, list):
                            print(f"{indent}   └─ (Liste avec {len(value)} éléments)")
        
        # Analyse spécifique des objets principaux (meteo et qualite_air)
        if city_data and "meteo" in city_data and "qualite_air" in city_data:
            # Analyse de l'objet meteo
            meteo_data = city_data["meteo"]
            meteo_paths = extract_field_paths(meteo_data)
            
            print("\n" + "="*100)
            print("STRUCTURE DÉTAILLÉE DES DONNÉES MÉTÉO")
            print("="*100)
            
            meteo_by_depth = defaultdict(list)
            for path in meteo_paths:
                depth = path.count(".")
                meteo_by_depth[depth].append(path)
            
            max_meteo_depth = max(meteo_by_depth.keys()) if meteo_by_depth else 0
            
            for depth in range(max_meteo_depth + 1):
                fields = sorted(meteo_by_depth[depth])
                print(f"\nNIVEAU {depth}:")
                print("-" * 40)
                
                for field in fields:
                    indent = "  " * depth
                    field_name = field.split(".")[-1] if "." in field else field
                    print(f"{indent}└─ {field_name}")
                    
                    # Pour le niveau 0, essayer d'afficher un exemple de valeur
                    parts = field.split(".")
                    try:
                        obj = meteo_data
                        for part in parts:
                            if part in obj:
                                obj = obj[part]
                            else:
                                obj = None
                                break
                        
                        if obj is not None and not isinstance(obj, (dict, list)):
                            print(f"{indent}   └─ Exemple: {obj}")
                    except:
                        pass
            
            # Analyse de l'objet qualite_air
            air_data = city_data["qualite_air"]
            air_paths = extract_field_paths(air_data)
            
            print("\n" + "="*100)
            print("STRUCTURE DÉTAILLÉE DES DONNÉES DE QUALITÉ D'AIR")
            print("="*100)
            
            air_by_depth = defaultdict(list)
            for path in air_paths:
                depth = path.count(".")
                air_by_depth[depth].append(path)
            
            max_air_depth = max(air_by_depth.keys()) if air_by_depth else 0
            
            for depth in range(max_air_depth + 1):
                fields = sorted(air_by_depth[depth])
                print(f"\nNIVEAU {depth}:")
                print("-" * 40)
                
                for field in fields:
                    indent = "  " * depth
                    field_name = field.split(".")[-1] if "." in field else field
                    print(f"{indent}└─ {field_name}")
                    
                    # Pour le niveau 0, essayer d'afficher un exemple de valeur
                    parts = field.split(".")
                    try:
                        obj = air_data
                        for part in parts:
                            if part in obj:
                                obj = obj[part]
                            else:
                                obj = None
                                break
                        
                        if obj is not None and not isinstance(obj, (dict, list)):
                            print(f"{indent}   └─ Exemple: {obj}")
                    except:
                        pass
        
        # Résumé final
        print("\n" + "="*100)
        print("RÉSUMÉ DES COLONNES")
        print("="*100)
        print(f"Nombre total de champs dans le fichier: {len(all_field_paths)}")
        
        if city_data:
            city_field_paths = extract_field_paths(city_data)
            print(f"Nombre de champs pour une ville: {len(city_field_paths)}")
            
            if "meteo" in city_data:
                meteo_paths = extract_field_paths(city_data["meteo"])
                print(f"Nombre de champs pour les données météo: {len(meteo_paths)}")
            
            if "qualite_air" in city_data:
                air_paths = extract_field_paths(city_data["qualite_air"])
                print(f"Nombre de champs pour les données de qualité d'air: {len(air_paths)}")
        
        print("="*100)
        
    except Exception as e:
        log(f"Erreur lors de l'analyse des colonnes: {str(e)}")
        import traceback
        log(traceback.format_exc())

if __name__ == "__main__":
    display_columns_by_level()