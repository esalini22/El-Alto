import requests, math
from flask import jsonify

#devuelve la distancia lineal en km
def distance(lat1: float, lat2: float, lng1: float, lng2: float):
    y = abs(lat1-lat2)*111.32
    x = abs(lng1-lng2)*111.32*math.cos((lat1+lat2)/2)
    return math.sqrt((x**2)+(y**2))

def check_args(args: str):
    if "lat" not in args:
        return None, "lat query parameter required"

    if "lng" not in args:
        return None, "lng query parameter required"

    if "product" not in args:
        return None, "product query parameter required"
    
    lat = args.get("lat", type=float)
    if lat is None:
        return None, "lat query parameter must be a float"
    
    lng  = args.get("lng", type=float)
    if lng is None:
        return None, "lng query parameter must be a float"
    
    if lat < -90 or lat > 90:
        return None, "invalid product lat parameter value"

    if lng < -180 or lng > 180:
        return None, "invalid lng query parameter value"
    
    product = args.get("product").lower()

    if product not in ("93", "95", "97", "diesel", "kerosene"):
        return None, "invalid product query parameter value"
    
    nearest_str = args.get("nearest", "false").lower()
    if nearest_str not in ("true", "false"):
        return None, "nearest query parameter must be 'true' or 'false'"
    
    store_str = args.get("store", "false").lower()
    if store_str not in ("true", "false"):
        return None, "store query parameter must be 'true' or 'false'"
    
    cheapest_str = args.get("cheapest", "false").lower()
    if cheapest_str not in ("true", "false"):
        return None, "cheapest query parameter must be 'true' or 'false'"
    
    nearest: bool = nearest_str == "true"
    store: bool = store_str == "true"
    cheapest: bool = cheapest_str == "true"
    
    return {"lat": lat, "lng": lng, "product": product, "nearest": nearest, "store": store, "cheapest": cheapest}, None

def init_marcas():
    response = requests.get("https://api.bencinaenlinea.cl/api/marca_ciudadano")
    try:
        resp_json = response.json()
    except (ValueError, requests.RequestException) as e:
        return None, e
    marcas = {}
    try:
        for f in resp_json["data"]:
            marcas[f["id"]] = f["nombre"]
    except (KeyError, TypeError, ValueError) as e:
        return None, e
    return marcas, None

def init_stations():
    response = requests.get("https://api.bencinaenlinea.cl/api/busqueda_estacion_filtro")

    try:
        resp_json = response.json()
        resp_data = resp_json["data"]
    except (ValueError, requests.RequestException) as e:
        return None, e
    
    return resp_data, None

#revisa que el json de la api bencinas tenga todos los campos necesarios
def check_stations_json(data):
    for item in data:
        if "id" not in item:
            return False
        if "marca" not in item:
            return False
        if "direccion" not in item:
            return False
        if "comuna" not in item:
            return False
        if "region" not in item:
            return False
        if "latitud" not in item:
            return False
        if "longitud" not in item:
            return False
        if "servicios" not in item:
            return False
        if "combustibles" not in item:
            return False
        for fuel in item["combustibles"]:
            if "nombre_corto" not in fuel:
                return False
            if "precio" not in fuel:
                return False
    return True
    
def station_has_store(id: int):
    response = requests.get(f"https://api.bencinaenlinea.cl/api/estacion_ciudadano/{id}")
    try:
        resp_json = response.json()
        for service in resp_json["data"]["servicios"]:
            if service["id"]==4:
                return True
    except (ValueError, requests.RequestException) as e:
        print(f"Response from external API was not store valid JSON: {e}")
        return False
    except requests.exceptions.Timeout as e:
        print(f"Timeout when fetching station {id}")
        return False
    except requests.exceptions.RequestException as e:
        print(f"Error fetching station {id}: {e}")
        return False
    return False

def find_price(data: dict[str, ], producto: str):
    total = 0
    for fuel in data:
        if producto == fuel["nombre_corto"]:
            if fuel["precio"] is None:
                continue
            price = fuel["precio"]

            #el punto es separador de decimales (y los decimales siempre son 0 en el precio)
            #nos quedamos con el lado izquierdo del punto
            if len(price.split(".")[0])>2:
                price = int(price.split(".")[0])

            #el punto es separador de miles
            #eliminamos el punto
            else:
                price = int(price.replace(".",""))
            total += price
    return total

def find_stations_with_store(data: dict[str, ]):
    stations = []
    for station in data:
        if station["tiene_tienda"] is True:
            stations.append(station)
    return stations

def find_nearest(data: dict[str, ]):
    stations = []
    lowestDistance = 21
    #primero buscamos la distancia lineal mas pequeña
    for station in data:
        if station["distancia(lineal)"] < lowestDistance:
            lowestDistance = station["distancia(lineal)"]
            
    #ahora la estacion a esa distancia
    for station in data:
        if station["distancia(lineal)"] == lowestDistance:
            stations.append(station)
            break

    return stations

def find_cheapest(data: dict[str, ], producto: str):
    lowestPrice: int = 2**31
    stations = []
    #primero buscamos el valor mas barato
    for station in data:
        if station["precios"+producto] > 0 and station["precios"+producto] < lowestPrice:
            lowestPrice = station["precios"+producto]
        elif station["preciosA"+producto] > 0 and station["preciosA"+producto] < lowestPrice:
            lowestPrice = station["preciosA"+producto]

    #ahora devolvemos todas las estaciones con ese valor
    for station in data:
        if station["precios"+producto] == lowestPrice or station["preciosA"+producto] == lowestPrice:
            stations.append(station)

    return stations