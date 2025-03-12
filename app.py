import pandas as pd
import requests
from minio import Minio
from minio.error import S3Error
import json
from io import BytesIO



Villes = [
    ["Paris", "Marseille", "Lyon", "Toulouse", "Nice", "Nantes", "Strasbourg", "Montpellier", "Bordeaux", "Lille", "Rennes", "Le Havre"],
    [48.8566, 43.2965, 45.7640, 43.6047, 43.7102, 47.2186, 48.5734, 43.6117, 44.8378, 50.6292, 48.1173, 49.4944],
    [2.3522, 5.3698, 4.8357, 1.4442, 7.2620, -1.5536, 7.7521, 3.8777, -0.5792, 3.0573, -1.6778, 0.1079]
]

air_api="https://api.waqi.info/feed/geo:{lat};{lon}/?token=ca9559f64030829280e1efe135d52fab54ca3d6e"
meteo_api="https://api.openweathermap.org/data/2.5/weather?lat={lat}&lon={lon}&appid=80f2502929bbdbaf3072277eb280a83f"


minio_client= Minio(
    "localhost:9000",
    access_key="minio",
    secret_key="minio123",
    secure=False
)


bucket_name = "meteo-villes"
try:

    if not minio_client.bucket_exists(bucket_name):
        minio_client.make_bucket(bucket_name)
except S3Error as e:
    print("Erreur lors de la création du bucket", e)


def get_meteo_data(lat, lon):
    url = meteo_api.format(lat=lat, lon=lon)
    response = requests.get(url)
    if response.status_code == 200:
        return response.json()
    else:
        return None
    
def get_air_data(lat, lon):
    url = air_api.format(lat=lat, lon=lon)
    response= requests.get(url)
    if response.status_code == 200:
        return response.json()
    else:
        return None
    
city_data=[]


for i in range(0, len(Villes[0])):
    name = Villes[0][i]
    lat = Villes[1][i]
    lon = Villes[2][i]

    meteo_info= get_meteo_data(lat, lon)
    air_info= get_air_data(lat, lon)

    if meteo_info and air_info:
        data = {
            "ville": name,
            "latitude": lat,
            "longitude": lon,
            "meteo": meteo_info,
            "qualite_air": air_info
        }

    city_data.append(data)
    json_data = json.dumps(data)
    byte_data = BytesIO(json_data.encode('utf-8'))
    file_name= f"{name}_meteo.json"
    minio_client.put_object(bucket_name, file_name, byte_data, length=len(byte_data.getvalue()))

df= pd.DataFrame(city_data)
print(df)
