import json, requests, math, sys
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
def distance(lat1, lat2, lng1, lng2):
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
    data = request.args

    print(data)

    if "lat" not in data:
        return jsonify({"success": False, "error": "lat query parameter required"}), 400

    if "lng" not in data:
        return jsonify({"success": False, "error": "lng query parameter required"}), 400

    if "product" not in data:
        return jsonify({"success": False, "error": "product query parameter required"}), 400

    lat = data.get("lat", type=float)
    lng = data.get("lat", type=float)
    product = data.get("product").lower()

    if lat < -90 or lat > 90:
        return jsonify({"success": False, "error": "invalid lat query parameter value"}), 400

    if lng < -180 or lat > 180:
        return jsonify({"success": False, "error": "invalid lng query parameter value"}), 400

    if product not in ("93", "95", "97", "diesel", "kerosene"):
        return jsonify({"success": False, "error": "invalid product query parameter value"}), 400

    nearest = data.get("nearest", "false").lower() == "true"
    store = data.get("store", "false").lower() == "true"
    cheapest = data.get("cheapest", "false").lower() == "true"

    #inicializamos el cache de estaciones
    if cache["stations"] is None or len(cache["stations"])==0:
        init_stations()

    #inicializamos el cache de marcas
    if cache["marcas"] is None or len(cache["marcas"])==0:
        init_marcas()

    #aqui se guardan las estaciones filtradas
    stations = []

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
            "distancia(lineal)": round(distance(lat, station_latitud, lng, station_longitud),10),
            "precios"+product: 0
        }

        '''
        #se deben manejar casos y excepciones en que datos de json esten mal formateados
        station["id"] = item["id"]
        station["compania"] = cache["marcas"][item["marca"]] #se debe sacar compañia de acuerdo a id de marca
        station["direccion"] = item["direccion"]
        station["comuna"] = item["comuna"]
        station["region"] = item["region"]
        station["latitud"] = float(item["latitud"].replace(",","."))
        station["longitud"] = float(item["longitud"].replace(",","."))
        #station["distancia(lineal)"] = "{:.2f}".format(distance(lat, station["latitud"], lng, station["longitud"]))
        #station["latitud"] = "{:.10f}".format(station["latitud"])
        #station["longitud"] = "{:.10f}".format(station["longitud"])
        station["precios"+product] = 0
        '''

        for fuel in item["combustibles"]:
            if product in fuel["nombre_largo"].lower():
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
                station["precios"+product] += price

        #estacion no contiene combustible filtrado
        if station["precios"+product] == 0:
            continue
        
        stations.append(station)

    #esto es lo que retornaremos
    result = stations

    #buscamos la mas barata
    if cheapest is True:
        lowestPrice = 2**31
        stations = []
        #primero buscamos el valor mas barato
        for station in result:
            if station["precios"+product] < lowestPrice:
                lowestPrice = station["precios"+product]

        print("lowestPrice: "+str(lowestPrice))

        #ahora devolvemos todas las estaciones con ese valor
        for station in result:
            if station["precios"+product] == lowestPrice:
                stations.append(station)

        result = stations

    #ahora buscamos la estacion mas cercana    
    #if nearest == True:

    #filtramos las que tienen tienda
    #if store == True:
        
    
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