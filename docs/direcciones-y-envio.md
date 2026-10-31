# Direcciones y costo de envío con Google (diseño, aún sin construir)

Hoy la clienta escribe su dirección en campos de texto (departamento, provincia, distrito, dirección) y el envío se cobra por **zona con tarifa fija** (`ShippingZone`). Esto sigue funcionando sin Google y es la opción de respaldo siempre.

Más adelante se puede mejorar con dos piezas independientes. Ninguna es necesaria para lanzar.

> Los precios y límites de abajo son los que se tienen en cuenta para decidir; **confírmalos en la página de precios de Google Maps Platform antes de activar la facturación**, porque cambian.

## 1. Autocompletar la dirección (Places Autocomplete)

- Se usa **solo en el navegador**, con la llave **restringida por dominio** (referrer) y limitada a la API de Places.
- **Siempre con sesiones** (`session token`): una sesión por dirección que escribe la clienta, usada en todas las pulsaciones y cerrada con la consulta final de detalles del lugar. Con la sesión bien hecha las pulsaciones no se cobran; **sin sesión se cobra cada tecla**. Es el error más caro y más fácil de cometer, por eso va con una prueba que verifique el token.
- El Maps Embed y los SDK móviles no tienen costo.
- Hay que **activar facturación con tarjeta** en Google Cloud aunque no se pase del tope gratuito.
- Los campos de texto actuales se mantienen: si Google falla o la clienta prefiere escribir, el pedido se hace igual.
- Requiere ajustar la CSP del frontend (`next.config.ts`) para permitir los dominios de Google Maps, y mencionar en la política de privacidad que la dirección que se escribe al autocompletar la procesa Google (Ley 29733).

## 2. Costo de envío por distancia en Lima (Routes + Geocoding)

- Un cálculo de ruta cuesta del orden de US$ 0,005 y se estima gratis hasta unas 10 000 consultas al mes. **Cuentan los intentos de checkout, no solo las ventas.**
- Las consultas a Routes y Geocoding se hacen **desde Django, nunca desde el navegador**, para no exponer esa llave.
- **Caché por dirección** normalizada (modelo propio con fecha): la misma dirección no se vuelve a consultar.
- Límite diario de consultas en Django (contador) y límite por IP/sesión; al pasarlos, o si Google no responde, se usa la **tarifa fija de la zona** y el pedido sigue.
- En Google Cloud: **alertas de presupuesto y cuotas máximas por día**, para que un error en el código no genere una factura grande.
- La tarifa por distancia se define en `ShippingZone` (tramos de km → precio) y la edita la administradora.

## 3. Envíos a provincia

Olva, Shalom y otros couriers **no se calculan con Google Maps**: cobran por destino y peso. Ahí se usa una **tabla de tarifas del courier** (destino y tramo de peso) cargada por la administradora. La clienta ve la tarifa antes de pagar.

## Qué hace falta para construirlo

1. Cuenta de Google Cloud con facturación activada (la crea el dueño del negocio con su tarjeta).
2. Dos llaves: una para el navegador (restringida por dominio) y otra para el servidor (restringida por IP del VPS), y alertas de presupuesto.
3. Las tarifas reales: tramos de distancia para Lima y tarifas de los couriers.

Hasta entonces, el checkout sigue con zonas de tarifa fija y esto queda registrado como mejora futura en el checklist de salida.
