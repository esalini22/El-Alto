import json
from flask import Flask, jsonify, request, Response
from utils.helpers import *

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

@app.route('/api/stations/search', methods=['GET'])
def stationsGET():
    DATA = request.args
    
    args, error = check_args(DATA)
    
    if error is not None:
        return jsonify({"success": False, "error": error}), 400

    #falta un type checking mas estrico en caso de que el input este mal
    LAT = args["lat"]
    LNG = args["lng"]
    PRODUCT = args["product"]
    NEAREST = args["nearest"]
    STORE = args["store"]
    CHEAPEST = args["cheapest"]
    
    #los productos en la API son 93, 95, 97, DI, y KE
    producto = PRODUCT[0:2].upper()
    
    #inicializamos el cache de estaciones
    if cache["stations"] is None or len(cache["stations"])==0:
        cache["stations"], error = init_stations()
        if error is not None:
            return jsonify({"success": False, "error": "Response from external API stations was not a valid JSON", "raw": error}), 502
        if check_stations_json(cache["stations"]) is False:
            return jsonify({"success": False, "error": "Response from external API stations was not a valid JSON"}), 502

    #inicializamos el cache de marcas
    if cache["marcas"] is None or len(cache["marcas"])==0:
        cache["marcas"], error = init_marcas()
        if error is not None:
            return jsonify({"success": False, "error": "Response from external API brands was not a valid JSON", "raw": error}), 502

    #aqui se guardan las estaciones filtradas
    stations: dict[str, ] = []

    #se filtra por tipo de producto
    #ademas estaciones deben estar dentro de radio de 20km
    for item in cache["stations"]:
        station_latitud = round(float(item["latitud"].replace(",",".")),10)
        station_longitud = round(float(item["longitud"].replace(",",".")),10)
        
        #estacion esta fuera de radio
        distancia_lineal = distance(LAT, station_latitud, LNG, station_longitud)
        if distancia_lineal>7:
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
            "distancia(lineal)": round(distancia_lineal,10),
            "precios"+producto: 0, #autoservicio
            "preciosA"+producto: 0, #asistido
            "tiene_tienda": item["tiene_tienda"]
        }

        #buscamos precio de producto
        station["precios"+producto] = find_price(item["combustibles"], producto)
        station["preciosA"+producto] = find_price(item["combustibles"], 'A'+producto)

        #estacion no contiene combustible filtrado
        #no se añade estacion a arreglo
        if station["precios"+producto] == 0 and station["preciosA"+producto] == 0:
            continue
        
        stations.append(station)

    #filtramos las que tienen tienda
    if STORE is True:
        stations = find_stations_with_store(stations)
        
    #buscamos la mas barata
    #aca se toma el producto ya sea autoservicio o asistido
    if CHEAPEST is True:
        stations = find_cheapest(stations, producto)
        
    #ahora buscamos la estacion mas cercana   
    #si es que el largo de result es mayor a 1
    if NEAREST is True and len(stations)>1:
        stations = find_nearest(stations)
    
    #no se usa jsonify para que no cambie orden de keys
    #return jsonify({"success": True, "data": result})

    if len(stations)==1:
        stations = stations[0]

    response = {"success": True, "data": stations}

    return Response(
        json.dumps(response, ensure_ascii=False, sort_keys=False),
        mimetype="application/json"
    )

if __name__ == '__main__':
    app.run(port=5000)