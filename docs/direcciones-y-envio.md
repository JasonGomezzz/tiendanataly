# Google Maps en la tienda: qué hace, cuánto cuesta y cómo se activa

Resumen para quien decide: la clienta verá **un mapa del punto de recojo** y, al escribir su dirección de delivery, **sugerencias de Google** que le completan departamento, provincia y distrito. Todo está construido y probado con un Google simulado; **se enciende con dos llaves de Google** y, sin ellas, la tienda funciona igual (enlace a Google Maps y dirección escrita a mano).

**Presupuesto previsto: S/ 39 al mes (unos US$ 10).** Se ponen como tope de gasto en Google Cloud, más un tope propio de llamadas por día en la tienda. Google exige registrar una **tarjeta** aunque el uso quede dentro del nivel gratuito.

## Qué verá la clienta

| Dónde | Qué ve | Costo |
|---|---|---|
| Checkout, al elegir «Recojo en punto de encuentro», y en la página de su pedido | Nombre y dirección del punto de recojo, mapa de Google incrustado y enlace «Abrir en Google Maps» | El mapa incrustado no tiene costo; el enlace tampoco y no necesita llave |
| Checkout, campo «Dirección» (delivery y provincias) | Sugerencias mientras escribe; al elegir una se llenan dirección, distrito, provincia y departamento. Todo se puede corregir a mano | Se cobra por sesión de búsqueda; ver «Costos y topes» |
| Costo de envío según la distancia en Lima | **No construido** (ver al final) | — |

## Cómo está construido (y por qué)

- **La llave secreta nunca llega al navegador.** Las sugerencias pasan por nuestro servidor (`/api/v1/places/autocomplete/` y `/places/detail/`); el navegador no carga ningún script de Google. Solo el mapa incrustado usa una llave pública, que se restringe por dominio.
- **Cobro por sesión.** Cada dirección que la clienta escribe usa una sesión (un código único) en todas las sugerencias y en la consulta final del lugar elegido. Así Google cobra la sesión completa y no cada tecla; sin sesión se cobra cada letra, que es el error caro de esta función.
- **Tope propio por día** (`GOOGLE_PLACES_DAILY_LIMIT`, 300 por defecto, sugerencias y detalle por separado). Al llegar al tope el buscador deja de sugerir y la clienta escribe a mano; el pedido sigue. El tope y la tarifa por minuto (`THROTTLE_PLACES`) acotan el gasto aunque alguien abuse.
- **No se guardan resultados de Google** (sus términos limitan guardarlos); solo se cuentan las llamadas del día.
- **Se pide solo Perú y en español**, y solo los campos necesarios del lugar (dirección, componentes y coordenadas).
- **Si Google falla**, el campo queda como uno normal. La política de privacidad ya explica que Google procesa lo que se escribe al usar las sugerencias.
- El mapa incrustado se permite en la política de seguridad del sitio (`frame-src https://www.google.com`).

## Costos y topes

- **Presupuesto:** en Google Cloud → *Facturación → Presupuestos y alertas*, crea uno de **S/ 39** (o su equivalente en dólares) con avisos al 50 %, 90 % y 100 %. **Un presupuesto avisa, no corta el gasto.** Para cortarlo, además:
  - fija una **cuota diaria** en cada API (*APIs y servicios → Cuotas*), y
  - deja `GOOGLE_PLACES_DAILY_LIMIT` en la tienda (300 por día como máximo: unas 9 000 sugerencias al mes).
- **Cuánto cuesta cada cosa** debe consultarse en la calculadora de precios de Google Maps Platform el día que se active, porque cambia. Referencia que se manejó al diseñar esto: el mapa incrustado es gratis; el autocompletado con sesión no cobra las pulsaciones si la sesión termina en una consulta de detalle; una ruta de Routes cuesta alrededor de US$ 0,005 y hay un nivel gratuito mensual. **Si el gasto proyectado supera S/ 39, baja `GOOGLE_PLACES_DAILY_LIMIT`.**
- Las sesiones que no terminan en una consulta de detalle (la clienta escribe y no elige nada) se cobran como solicitudes sueltas; el tope diario las acota.

## Qué hace falta (lo hace el dueño del negocio)

1. **Google Cloud:** crear un proyecto en console.cloud.google.com, activar la facturación y registrar la tarjeta.
2. **Activar dos APIs:** *Maps Embed API* y *Places API (New)*.
3. **Crear dos llaves** (*APIs y servicios → Credenciales*):
   - **Pública**, para el mapa: restricción de aplicación = *Sitios web (referentes HTTP)* con `https://TU-DOMINIO/*`; restricción de API = solo *Maps Embed API*. Va en `GOOGLE_MAPS_EMBED_KEY`.
   - **Secreta**, para las sugerencias: restricción de aplicación = *Direcciones IP* con la IP del VPS; restricción de API = solo *Places API (New)*. Va en `GOOGLE_PLACES_KEY`.
4. **Presupuesto y cuotas** como se explica arriba.
5. **En el servidor:** poner las dos llaves y `GOOGLE_PLACES_DAILY_LIMIT` en `.env.prod` y reiniciar el backend (`docker compose ... up -d backend`).
6. **En el panel** (`/admin` → Ajustes → *Recojo*): escribir el nombre y la dirección del punto de recojo, tal como se buscaría en Google Maps (por ejemplo «Parque Kennedy, Miraflores, Lima»). Mientras no haya dirección, no se muestra mapa.

## Lista de verificación al activar (no se probó con una llave real de Google)

El formato de las respuestas de Google se tomó de su documentación y se probó contra un simulador local, no contra Google. Al activar:

- [ ] En el checkout, escribir una dirección real de Lima: aparecen sugerencias y, al elegir una, se llenan distrito, provincia y departamento correctos.
- [ ] Probar una dirección de provincia (por ejemplo Arequipa o Cusco) y revisar que departamento y provincia salgan bien; si no, ajustar `parse_place` en `apps/shipping/places.py`.
- [ ] Mirar en Google Cloud → *APIs y servicios → Métricas* que las llamadas de autocompletado y de detalle sean parecidas (señal de que las sesiones se cierran bien).
- [ ] Probar el tope: bajar `GOOGLE_PLACES_DAILY_LIMIT` a 3 y comprobar que, pasado el tope, el campo deja de sugerir y el pedido se puede hacer.
- [ ] Abrir el mapa en el celular y confirmar que carga y que el enlace abre la aplicación de Google Maps.

## Lo que queda para después (no construido)

- **Costo de envío por distancia en Lima** con Routes: se llama desde el servidor con caché de coordenadas (lo único que Google permite guardar, hasta 30 días), tope diario y respaldo en la tarifa fija de la zona. Necesita las tarifas por tramo de kilómetros.
- **Envíos a provincia** (Olva, Shalom y similares): no se calculan con Google Maps; se cobra por tarifa del courier (destino y peso) en una tabla que carga la administradora.
