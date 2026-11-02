"""Direcciones sugeridas con Google Places (API nueva), llamadas SIEMPRE desde el servidor.

Por qué desde el servidor:
- La llave vive solo aquí; el navegador nunca la ve (no hay nada que robar ni que restringir por dominio).
- Hay un tope propio por día (GOOGLE_PLACES_DAILY_LIMIT): aunque alguien abuse del buscador, el costo no pasa
  de lo previsto. Al llegar al tope el buscador deja de sugerir y el checkout sigue con la dirección escrita.
- No se guardan resultados de Google (sus términos limitan el almacenamiento); solo contadores del día.

Cobro por sesión: cada vez que la clienta empieza a escribir, el navegador genera un `session` (UUID) y lo usa en
todas las sugerencias y en la consulta final del lugar elegido. Así Google cobra la sesión completa y no cada tecla.

AVISO: el formato de las respuestas de Google está tomado de su documentación y NO se probó con una llave real
(ver docs/direcciones-y-envio.md, lista de verificación al activar).
"""
import json
import logging
import re
import urllib.error
import urllib.parse
import urllib.request

from django.conf import settings
from django.core.cache import cache
from django.utils import timezone

logger = logging.getLogger(__name__)

TIMEOUT = 5
SESSION_RE = re.compile(r"^[0-9a-fA-F-]{36}$")
PLACE_ID_RE = re.compile(r"^[A-Za-z0-9_-]{10,200}$")
MAX_SUGGESTIONS = 5


class PlacesUnavailable(Exception):
    """Google no respondió bien (red, tiempo agotado o respuesta inválida)."""


def enabled():
    return bool(settings.GOOGLE_PLACES_KEY)


def _request_json(url, *, method="GET", body=None, headers=None):
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(
        url, data=data, method=method,
        headers={"Content-Type": "application/json", "X-Goog-Api-Key": settings.GOOGLE_PLACES_KEY, **(headers or {})},
    )
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT) as response:  # noqa: S310 - URL fija de Google
            return json.loads(response.read() or b"{}")
    except (urllib.error.URLError, TimeoutError, ValueError) as exc:
        # No se registra la URL completa ni las cabeceras (llevan la llave).
        raise PlacesUnavailable(type(exc).__name__) from exc


def _spend(kind):
    """Cuenta una llamada a Google. Devuelve False si ya se llegó al tope de hoy."""
    key = f"places:{timezone.localdate().isoformat()}:{kind}"
    cache.add(key, 0, 60 * 60 * 26)
    used = cache.incr(key)
    if used > settings.GOOGLE_PLACES_DAILY_LIMIT:
        if used == settings.GOOGLE_PLACES_DAILY_LIMIT + 1:
            logger.warning("Google Places: se llegó al tope diario de %s (%s).", settings.GOOGLE_PLACES_DAILY_LIMIT, kind)
        return False
    return True


def autocomplete(query, session):
    """Hasta 5 sugerencias de dirección en Perú. Lista vacía si se llegó al tope diario."""
    text = " ".join(query.split())[:120]
    if not _spend("autocomplete"):
        return []
    data = _request_json(
        f"{settings.GOOGLE_PLACES_BASE}/places:autocomplete", method="POST",
        body={"input": text, "sessionToken": session, "includedRegionCodes": ["pe"], "languageCode": "es"},
    )
    out = []
    for item in data.get("suggestions", []):
        prediction = item.get("placePrediction") or {}
        place_id = prediction.get("placeId") or str(prediction.get("place", "")).removeprefix("places/")
        label = (prediction.get("text") or {}).get("text", "")
        fmt = prediction.get("structuredFormat") or {}
        if place_id and label:
            out.append({
                "id": place_id,
                "texto": label,
                "principal": (fmt.get("mainText") or {}).get("text", "") or label,
                "secundario": (fmt.get("secondaryText") or {}).get("text", ""),
            })
    return out[:MAX_SUGGESTIONS]


def _clean_admin(name):
    value = name.strip()
    for prefix in ("Provincia de ", "Departamento de ", "Región ", "Region "):
        if value.startswith(prefix):
            value = value[len(prefix):]
    for suffix in (" Province", " Region", " Provincia", " Región", " Department"):
        if value.endswith(suffix):
            value = value[: -len(suffix)]
    return value.strip()


def parse_place(data):
    """Convierte el lugar de Google en los campos del checkout (departamento, provincia, distrito, dirección)."""
    by_type = {}
    for comp in data.get("addressComponents", []):
        for kind in comp.get("types", []):
            by_type.setdefault(kind, comp.get("longText", ""))
    formatted = data.get("formattedAddress", "")
    route, number = by_type.get("route", ""), by_type.get("street_number", "")
    direccion = f"{route} {number}".strip() if route else formatted.split(",")[0].strip()
    location = data.get("location") or {}
    return {
        "direccion": direccion,
        "distrito": by_type.get("locality") or by_type.get("sublocality_level_1") or by_type.get("administrative_area_level_3", ""),
        "provincia": _clean_admin(by_type.get("administrative_area_level_2", "")),
        "departamento": _clean_admin(by_type.get("administrative_area_level_1", "")),
        "formateada": formatted,
        "lat": location.get("latitude"),
        "lng": location.get("longitude"),
    }


def place_details(place_id, session):
    """Datos del lugar elegido; cierra la sesión de cobro. None si ya se llegó al tope diario."""
    if not _spend("detalle"):
        return None
    query = urllib.parse.urlencode({"languageCode": "es", "sessionToken": session})
    data = _request_json(
        f"{settings.GOOGLE_PLACES_BASE}/places/{urllib.parse.quote(place_id, safe='')}?{query}",
        headers={"X-Goog-FieldMask": "formattedAddress,addressComponents,location"},
    )
    return parse_place(data)
