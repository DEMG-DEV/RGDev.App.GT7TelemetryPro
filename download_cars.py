import urllib.request
import csv
import json
import os

print("Descargando base de datos de GT7...")
cars_url = "https://raw.githubusercontent.com/ddm999/gt7info/web-new/_data/db/cars.csv"
makers_url = "https://raw.githubusercontent.com/ddm999/gt7info/web-new/_data/db/maker.csv"

def download_csv(url):
    response = urllib.request.urlopen(url)
    lines = [l.decode('utf-8') for l in response.readlines()]
    reader = csv.reader(lines)
    header = next(reader)
    return header, list(reader)

try:
    c_header, c_data = download_csv(cars_url)
    m_header, m_data = download_csv(makers_url)
    
    # Construir diccionario de marcas
    makers = {}
    for row in m_data:
        if len(row) >= 2:
            makers[row[0]] = row[1]
            
    # Construir base de datos de autos final
    cars_json = {}
    for row in c_data:
        if len(row) >= 3:
            car_id = int(row[0])
            short_name = row[1]
            maker_id = row[2]
            maker_name = makers.get(maker_id, "Unknown Maker")
            
            # Guardamos el carro con su marca
            cars_json[str(car_id)] = {
                "id": car_id,
                "maker": maker_name,
                "name": short_name,
                "full_name": f"{maker_name} {short_name}"
            }
            
    json_path = "gt7_cars.json"
    with open(json_path, 'w', encoding='utf-8') as f:
        json.dump(cars_json, f, indent=4, ensure_ascii=False)
        
    print(f"Éxito: Se guardaron {len(cars_json)} autos en {json_path}")
    
except Exception as e:
    print("Error:", e)
