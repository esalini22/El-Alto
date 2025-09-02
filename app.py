import json, requests, math
from flask import Flask, jsonify, request, Response

app = Flask(__name__)
app.config["JSON_SORT_KEYS"] = False

'''
endpoints api bencinas:
    https://api.bencinaenlinea.cl/api/busqueda_estacion_filtro
    https://api.bencinaenlinea.cl/api/combustible_ciudadano
    https://api.bencinaenlinea.cl/api/marca_ciudadano
    https://api.bencinaenlinea.cl/api/servicio_ciudadano -> tienda es id: 4
    https://api.bencinaenlinea.cl/api/estacion_ciudadano/{id}
'''

#json de estaciones y dict de marcas
cache = { "stations": None, "marcas": {} }

#devuelve la distancia euclideana
def distance(lat1: float, lat2: float, lng1: float, lng2: float):
    return math.sqrt(abs(lat1-lat2)**2+abs(lng1-lng2)**2)

#devuelve la distancia lineal en km
def in_radius(lat1: float, lat2: float, lng1: float, lng2: float):
    y = abs(lat1-lat2)*111.32
    x = abs(lng1-lng2)*111.32*math.cos((lat1+lat2)/2)
    return math.sqrt((x**2)+(y**2))

def init_marcas():
    response = requests.get("https://api.bencinaenlinea.cl/api/marca_ciudadano")
    try:
        resp_json = response.json()
    except ValueError:
        return jsonify({"success": False, "error": "Response from external API was not valid JSON", "raw": response.text}), 502
    marcas = {}
    for f in resp_json["data"]:
        marcas[f["id"]] = f["nombre"]
    cache["marcas"] = marcas

def init_stations():
    response = requests.get("https://api.bencinaenlinea.cl/api/busqueda_estacion_filtro")

    try:
        resp_json = response.json()
    except ValueError:
        return jsonify({"success": False, "error": "Response from external API was not valid JSON", "raw": response.text}), 502
    
    cache["stations"] = resp_json["data"]
    
def station_has_store(id: int):
    response = requests.get(f"https://api.bencinaenlinea.cl/api/estacion_ciudadano/{id}")
    try:
        resp_json = response.json()
        for service in resp_json["data"]["servicios"]:
            if service["id"]==4:
                return True
    except ValueError:
        return jsonify({"success": False, "error": "Response from external API was not valid JSON", "raw": response.text}), 502
    return False

@app.route('/api/stations/search', methods=['GET'])
def stationsGET():
    DATA = request.args

    if "lat" not in DATA:
        return jsonify({"success": False, "error": "lat query parameter required"}), 400

    if "lng" not in DATA:
        return jsonify({"success": False, "error": "lng query parameter required"}), 400

    if "product" not in DATA:
        return jsonify({"success": False, "error": "product query parameter required"}), 400

    #falta un type checking mas estrico en caso de que el input este mal
    LAT: float = DATA.get("lat", type=float)
    LNG: float  = DATA.get("lng", type=float)
    PRODUCT: str  = DATA.get("product").lower()

    if LAT < -90 or LAT > 90:
        return jsonify({"success": False, "error": "invalid lat query parameter value"}), 400

    if LNG < -180 or LNG > 180:
        return jsonify({"success": False, "error": "invalid lng query parameter value"}), 400

    if PRODUCT not in ("93", "95", "97", "diesel", "kerosene"):
        return jsonify({"success": False, "error": "invalid product query parameter value"}), 400

    NEAREST: bool = DATA.get("nearest", "false").lower() == "true"
    STORE: bool = DATA.get("store", "false").lower() == "true"
    CHEAPEST: bool = DATA.get("cheapest", "false").lower() == "true"

    #inicializamos el cache de estaciones
    if cache["stations"] is None or len(cache["stations"])==0:
        init_stations()

    #inicializamos el cache de marcas
    if cache["marcas"] is None or len(cache["marcas"])==0:
        init_marcas()

    #aqui se guardan las estaciones filtradas
    stations: dict[str, ] = []

    #se filtra por tipo de producto
    #ademas estaciones deben estar dentro de radio de 20km
    for item in cache["stations"]:
        station_latitud = round(float(item["latitud"].replace(",",".")),10)
        station_longitud = round(float(item["longitud"].replace(",",".")),10)
        
        #estacion esta fuera de radio
        radius = in_radius(LAT, station_latitud, LNG, station_longitud)
        if radius>20:
            continue
        
        if "tiene_tienda" not in item:
            tiene_tienda = len(item["servicios"])>0 and station_has_store(item["id"])
            item["tiene_tienda"] = tiene_tienda

        station = {
            "id": item["id"],
            "compania": cache["marcas"][item["marca"]], #se debe sacar compañia de acuerdo a id de marca
            "direccion": item["direccion"],
            "comuna": item["comuna"],
            "region": item["region"],
            "latitud": station_latitud,
            "longitud": station_longitud,
            "distancia(lineal)": round(distance(LAT, station_latitud, LNG, station_longitud),10),
            "precios"+PRODUCT: 0,
            "tiene_tienda": item["tiene_tienda"]
        }

        for fuel in item["combustibles"]:
            if PRODUCT in fuel["nombre_largo"].lower():
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
                station["precios"+PRODUCT] += price

        #estacion no contiene combustible filtrado
        #no se añade estacion a arreglo
        if station["precios"+PRODUCT] == 0:
            continue
        
        stations.append(station)

    #esto es lo que retornaremos
    result = stations

    #filtramos las que tienen tienda
    if STORE is True:
        stations = []
        for station in result:
            if station["tiene_tienda"] is True:
                stations.append(station)
        result = stations
        
    #buscamos la mas barata
    if CHEAPEST is True:
        lowestPrice: int = 2**31
        stations = []
        #primero buscamos el valor mas barato
        for station in result:
            if station["precios"+PRODUCT] < lowestPrice:
                lowestPrice = station["precios"+PRODUCT]

        #ahora devolvemos todas las estaciones con ese valor
        for station in result:
            if station["precios"+PRODUCT] == lowestPrice:
                stations.append(station)

        result = stations
        
    #ahora buscamos la estacion mas cercana    
    #si es que el largo de result es mayor a 1
    if NEAREST is True and len(result)>1:
        stations = []
        lowestDistance = 21
        #primero buscamos la distancia lineal mas pequeña
        for station in result:
            if station["distancia(lineal)"] < lowestDistance:
                lowestDistance = station["distancia(lineal)"]
                
        #ahora la estacion a esa distancia
        for station in result:
            if station["distancia(lineal)"] == lowestDistance:
                stations.append(station)
                break
                
        result = stations        
    
    #no se usa jsonify para que no cambie orden de keys
    #return jsonify({"success": True, "data": result})

    if len(result)==1:
        result = result[0]

    response = {"success": True, "data": result}

    return Response(
        json.dumps(response, ensure_ascii=False, sort_keys=False),
        mimetype="application/json"
    )

if __name__ == '__main__':
    app.run(port=5000)