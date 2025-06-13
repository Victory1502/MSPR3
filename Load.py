import pandas as pd
from sqlalchemy import create_engine

def load():
    try:
        csv_file = "donnees_completes.csv"
        # ✅ Utilisez le port interne 5432 au lieu de 15432
        engine = create_engine('postgresql+psycopg2://admin:admin123@postgres:5432/mspr3')

        df = pd.read_csv(csv_file, encoding='utf-8-sig')
        df.columns = [
            'ville', 'latitude', 'longitude', 'timestamp_meteo',
            'temperature_k', 'temperature_c', 'temperature_ressentie_k', 'temperature_ressentie_c',
            'pression', 'humidite', 'condition_meteo', 'description_meteo',
            'visibilite', 'vitesse_vent', 'direction_vent', 'couverture_nuageuse',
            'aqi', 'polluant_dominant', 'pm25', 'pm10', 'o3', 'no2', 'horodatage_aqi'
        ]

        df.to_sql('meteo_air_quality', engine, if_exists='append', index=False)
        print("✅ Données chargées dans la table 'meteo_air_quality' avec succès.")

    except Exception as e:
        print(f"❌ Erreur lors du chargement des données : {e}")
        raise

if __name__ == "__main__":
    load()