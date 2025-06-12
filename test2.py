import pandas as pd
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.exc import ProgrammingError
import os

csv_file = "donnees_completes.csv"

# Set environment variables to force UTF-8
os.environ['PGCLIENTENCODING'] = 'UTF8'

# Multiple solutions - try them in order:

# Solution 1: Most likely to work - explicit client encoding
try:
    engine = create_engine(
        'postgresql://admin:admin123@localhost:5432/mspr3?client_encoding=utf8',
        connect_args={"client_encoding": "utf8"}
    )
    print("Tentative de connexion avec client_encoding=utf8...")
except Exception as e:
    print(f"Solution 1 échouée : {e}")
    
    # Solution 2: Try without explicit encoding parameter
    try:
        engine = create_engine(
            'postgresql://admin:admin123@localhost:5432/mspr3?client_encoding=utf8'
        )
        print("Tentative de connexion avec URL encoding...")
    except Exception as e:
        print(f"Solution 2 échouée : {e}")
        
        # Solution 3: Try with latin-1 encoding
        try:
            engine = create_engine(
                'postgresql://admin:admin123@localhost:5432/mspr3',
                connect_args={"client_encoding": "latin1"}
            )
            print("Tentative de connexion avec latin-1...")
        except Exception as e:
            print(f"Solution 3 échouée : {e}")
            print("Toutes les tentatives de connexion ont échoué.")
            exit(1)

# Alternative Solution 2: Use psycopg2 connection parameters
# engine = create_engine(
#     'postgresql://admin:admin123@localhost:5432/mspr3',
#     connect_args={"client_encoding": "utf8"}
# )

# Alternative Solution 3: If database has Latin-1/ISO-8859-1 encoding
# engine = create_engine(
#     'postgresql://admin:admin123@localhost:5432/mspr3',
#     encoding='latin-1'
# )

try:
    inspector = inspect(engine)
    print("Connexion à la base de données réussie.")
except Exception as e:
    print(f"Erreur de connexion : {e}")
    exit(1)

# Read CSV file
try:
    df = pd.read_csv(csv_file, encoding='utf-8-sig')
    print(f"CSV lu avec succès. Nombre de lignes : {len(df)}")
except Exception as e:
    print(f"Erreur lors de la lecture du CSV : {e}")
    # Try alternative encodings
    try:
        df = pd.read_csv(csv_file, encoding='latin-1')
        print(f"CSV lu avec encoding latin-1. Nombre de lignes : {len(df)}")
    except Exception as e2:
        print(f"Erreur avec latin-1 aussi : {e2}")
        exit(1)

# Rename columns
df.columns = [
    'ville', 'latitude', 'longitude', 'timestamp_meteo',
    'temperature_k', 'temperature_c', 'temperature_ressentie_k', 'temperature_ressentie_c',
    'pression', 'humidite', 'condition_meteo', 'description_meteo',
    'visibilite', 'vitesse_vent', 'direction_vent', 'couverture_nuageuse',
    'aqi', 'polluant_dominant', 'pm25', 'pm10', 'o3', 'no2', 'horodatage_aqi'
]

# Check if table exists and create if necessary
if not inspector.has_table('meteo_air_quality'):
    create_table_query = text("""
    CREATE TABLE meteo_air_quality (
        id SERIAL PRIMARY KEY,
        ville TEXT,
        latitude FLOAT,
        longitude FLOAT,
        timestamp_meteo TIMESTAMP,
        temperature_k FLOAT,
        temperature_c FLOAT,
        temperature_ressentie_k FLOAT,
        temperature_ressentie_c FLOAT,
        pression INT,
        humidite INT,
        condition_meteo TEXT,
        description_meteo TEXT,
        visibilite INT,
        vitesse_vent FLOAT,
        direction_vent INT,
        couverture_nuageuse INT,
        aqi INT,
        polluant_dominant TEXT,
        pm25 FLOAT,
        pm10 FLOAT,
        o3 FLOAT,
        no2 FLOAT,
        horodatage_aqi TIMESTAMP
    );
    """)
    
    try:
        with engine.connect() as connection:
            connection.execute(create_table_query)
            connection.commit()
        print("Table 'meteo_air_quality' créée avec succès.")
    except ProgrammingError as e:
        print(f"Erreur lors de la création de la table : {e}")
        exit(1)
else:
    print("La table 'meteo_air_quality' existe déjà.")

# Insert data into table
try:
    df.to_sql('meteo_air_quality', engine, if_exists='append', index=False)
    print("Données chargées dans la table 'meteo_air_quality' avec succès.")
except Exception as e:
    print(f"Erreur lors de l'insertion des données : {e}")