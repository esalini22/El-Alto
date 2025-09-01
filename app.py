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

#json de estaciones y dict de tipos de combustible
cache = { "stations": None, "fuel": {}, "marcas": {} }

#pitagoras
def distance(lat1: float, lat2: float, lng1: float, lng2: float):
    return math.sqrt(abs(lat1-lat2)**2+abs(lng1-lng2)**2)

#filtered = [s for s in stations_cache["data"] if s["ubicacion"]["latitud"]=="direccion"]

'''def init_fuel():
    response = requests.get("https://api.bencinaenlinea.cl/api/combustible_ciudadano")
    try:
        resp_json = response.json()
    except ValueError:
        return jsonify({"success": False, "error": "Response from external API was not valid JSON", "raw": response.text}), 502
    fuel = {}
    for f in resp_json["data"]:
        fuel[f["nombre_corto"]] = f["id"]'''

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
    
    cache["stations"] = resp_json

@app.route('/api/stations/search', methods=['GET'])
def stationsGET():
    DATA = request.args

    print(DATA)

    if "lat" not in DATA:
        return jsonify({"success": False, "error": "lat query parameter required"}), 400

    if "lng" not in DATA:
        return jsonify({"success": False, "error": "lng query parameter required"}), 400

    if "product" not in DATA:
        return jsonify({"success": False, "error": "product query parameter required"}), 400

    #falta un type checking mas estrico en caso de que el input este mal
    LAT: float = DATA.get("lat", type=float)
    LNG: float  = DATA.get("lat", type=float)
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
    for item in cache["stations"]["data"]:
        station_latitud = round(float(item["latitud"].replace(",",".")),10)
        station_longitud = round(float(item["longitud"].replace(",",".")),10)

        station = {
            "id": item["id"],
            "compania": cache["marcas"][item["marca"]], #se debe sacar compañia de acuerdo a id de marca
            "direccion": item["direccion"],
            "comuna": item["comuna"],
            "region": item["region"],
            "latitud": station_latitud,
            "longitud": station_longitud,
            "distancia(lineal)": round(distance(LAT, station_latitud, LNG, station_longitud),10),
            "precios"+PRODUCT: 0
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

    #buscamos la mas barata
    if CHEAPEST is True:
        lowestPrice: int = 2**31
        stations = []
        #primero buscamos el valor mas barato
        for station in result:
            if station["precios"+PRODUCT] < lowestPrice:
                lowestPrice = station["precios"+PRODUCT]

        print("lowestPrice: "+str(lowestPrice))

        #ahora devolvemos todas las estaciones con ese valor
        for station in result:
            if station["precios"+PRODUCT] == lowestPrice:
                stations.append(station)

        result = stations

    #ahora buscamos la estacion mas cercana    
    #if NEAREST is True:

    #filtramos las que tienen tienda
    #if STORE is True:
        
    
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