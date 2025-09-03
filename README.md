Para levantar la API,s e debe instalar la librería `Flask`, y luego ejecutar desde una terminal de linux `python3 app.py`
 

El programa se divide en `app.py` y `utils/helpers.py`, este último archivo contiene funciones de utilidad para la API, tales como funciones para inicializar la cache con los datos de las estaciones, calcular la distancia entre dos coordenadas y expresarlo en km, y filtrar las estaciones.

La API se ejecuta en el puerto 5000.

Para utilizar la API, se debe hacer uso de un cliente REST como Postman o VSCode con la extension REST Client.

El endpoint de la API es `/api/stations/search?lat={latitud}&lng={longitud}&product={producto}&nearest={bool}&store={bool}&cheapest={bool}`

El valor de `lat` es un `float` entre -90 y 90.

El valor de `lng` es un `float` entre -180 y 180.

El valor de `product` es un `string` y debe estar dentro de ("93", "95", "97", "diesel", "kerosene").

Los demás parámetros son opcionales y deben tomar un valor `boolean` ("true" o "false"):
- `nearest`: Este valor devuelve la estación más cercana.
- `cheapest`: Este valor devuelve las estaciones con el precio del producto especificado más bajo.
- `store`: Este valor devuelve las estaciones que poseen tienda.

La API es más rápida con usos subsecuentes, ya que en el primer uso debe cargar la data de las estaciones dentro del radio para las coordenadas dadas.

Solo hace uso de estaciones dentro de un radio de aproximadamente 7km alrededor de las coordenadas dadas (se consideró inicialmente un radio de 20km, pero se redujo para para disminuir el tiempo de ejecución de la API).

Guarda el precio de un producto tanto en su modalidad autoservicio como asistido (prefijo `A`).

Para la búsqueda de la estación con el precio más bajo para el producto dado, considera el precio tanto en modalidad autoservicio como asistido.

Ejemplo de respuesta para `/api/stations/search?lat=-33.4290062&lng=-70.6228354&product=kerosene&nearest=true&store=true&cheapest=true`

```
{
    "success": true,
    "data": {
        "id": 1949,
        "compania": "SHELL",
        "direccion": "San Ignacio 2470",
        "comuna": "San Miguel",
        "region": "Metropolitana de Santiago",
        "latitud": -33.4771200551,
        "longitud": -70.6535643339,
        "distancia(lineal)": 5.57,
        "preciosKE": 1060,
        "tiene_tienda": true
    }
}
```
