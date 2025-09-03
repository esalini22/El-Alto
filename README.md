Para levantar la API, ejecutar desde una terminal de linux `python3 app.py`

La API se ejecuta en el puerto 5000.

Para utilizar la API, se debe hacer uso de un cliente REST como Postman o VSCode con la extension REST Client.

El endpoint de la API es `/api/stations/search?lat={latitud}&lng={longitud}&product={producto}&nearest={bool}&store={bool}&cheapest={bool}`

El valor de `lat` es un `float` entre -90 y 90.

El valor de `lng` es un `float` entre -180 y 180.

El valor de `product` es un `string` y debe estar dentro de ("93", "95", "97", "diesel", "kerosene").

Los demás parámetros son opcionales y deben tomar un valor `boolean` ("true" o "false").

La API es más rápida con usos subsecuentes, ya que en el primer uso debe cargar la data de las estaciones dentro del radio para las coordenadas dadas.

Solo hace uso de estaciones dentro de un radio de aproximadamente 20km alrededor de las coordenadas dadas.

Guarda el precio de un producto tanto en su modalidad autoservicio como asistido (prefijo `A`).

Para la búsqueda de la estación con el precio más bajo para el producto dado, considera el precio tanto en modalidad autoservicio como asistido.