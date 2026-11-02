import uuid

import pytest
from django.core.cache import cache

from apps.core.models import StoreSettings
from apps.shipping import places

pytestmark = pytest.mark.django_db

LLAVE = "llave-secreta-solo-del-servidor"

LUGAR_MIRAFLORES = {
    "formattedAddress": "Av. Larco 345, Miraflores 15074, Perú",
    "location": {"latitude": -12.1219, "longitude": -77.0297},
    "addressComponents": [
        {"longText": "345", "types": ["street_number"]},
        {"longText": "Avenida Larco", "types": ["route"]},
        {"longText": "Miraflores", "types": ["locality", "political"]},
        {"longText": "Lima", "types": ["administrative_area_level_2", "political"]},
        {"longText": "Lima Province", "types": ["administrative_area_level_1", "political"]},
    ],
}

SUGERENCIAS = {
    "suggestions": [
        {"placePrediction": {
            "place": "places/ChIJabcdefghij12345", "placeId": "ChIJabcdefghij12345",
            "text": {"text": "Av. Larco 345, Miraflores, Perú"},
            "structuredFormat": {"mainText": {"text": "Av. Larco 345"}, "secondaryText": {"text": "Miraflores, Perú"}},
        }},
        {"queryPrediction": {"text": {"text": "larco"}}},  # sin lugar: se ignora
    ]
}


@pytest.fixture(autouse=True)
def limpio(settings):
    cache.clear()
    settings.GOOGLE_PLACES_KEY = LLAVE
    settings.GOOGLE_PLACES_DAILY_LIMIT = 300


@pytest.fixture
def google(monkeypatch):
    """Google falso: guarda lo que se le pidió y responde lo que cada prueba defina."""
    class Falso:
        llamadas = []
        respuesta = {}

    def fake(url, *, method="GET", body=None, headers=None):
        Falso.llamadas.append({"url": url, "method": method, "body": body, "headers": headers or {}})
        if isinstance(Falso.respuesta, Exception):
            raise Falso.respuesta
        return Falso.respuesta

    Falso.llamadas = []
    monkeypatch.setattr(places, "_request_json", fake)
    return Falso


def sesion():
    return str(uuid.uuid4())


def test_sin_llave_el_buscador_esta_apagado(api, settings):
    settings.GOOGLE_PLACES_KEY = ""
    assert api.get("/api/v1/places/autocomplete/", {"q": "larco 345", "session": sesion()}).status_code == 503
    assert api.get("/api/v1/store-settings/public/").json()["direcciones_google"] is False


def test_exige_sesion_y_un_minimo_de_letras(api, google):
    assert api.get("/api/v1/places/autocomplete/", {"q": "larco 345"}).status_code == 400
    assert api.get("/api/v1/places/autocomplete/", {"q": "larco 345", "session": "no-es-uuid"}).status_code == 400
    assert api.get("/api/v1/places/autocomplete/", {"q": "la", "session": sesion()}).status_code == 400
    assert google.llamadas == []


def test_las_sugerencias_se_normalizan_y_se_pide_solo_peru_en_espanol(api, google):
    google.respuesta = SUGERENCIAS
    s = sesion()
    r = api.get("/api/v1/places/autocomplete/", {"q": "larco 345", "session": s})
    assert r.status_code == 200
    assert r.json()["sugerencias"] == [{"id": "ChIJabcdefghij12345", "texto": "Av. Larco 345, Miraflores, Perú", "principal": "Av. Larco 345", "secundario": "Miraflores, Perú"}]
    pedido = google.llamadas[0]
    assert pedido["body"]["includedRegionCodes"] == ["pe"] and pedido["body"]["languageCode"] == "es"
    assert pedido["body"]["sessionToken"] == s
    assert pedido["url"].startswith("https://places.googleapis.com/")


def test_si_google_falla_el_checkout_sigue_sin_sugerencias(api, google):
    google.respuesta = places.PlacesUnavailable("URLError")
    r = api.get("/api/v1/places/autocomplete/", {"q": "larco 345", "session": sesion()})
    assert r.status_code == 200 and r.json() == {"sugerencias": []}


def test_el_tope_diario_corta_las_llamadas_a_google(api, google, settings):
    settings.GOOGLE_PLACES_DAILY_LIMIT = 2
    google.respuesta = SUGERENCIAS
    resultados = [api.get("/api/v1/places/autocomplete/", {"q": "larco 345", "session": sesion()}).json()["sugerencias"] for _ in range(4)]
    assert [bool(x) for x in resultados] == [True, True, False, False]
    assert len(google.llamadas) == 2  # nunca se pasó del tope


def test_el_detalle_separa_departamento_provincia_distrito_y_direccion(api, google):
    google.respuesta = LUGAR_MIRAFLORES
    s = sesion()
    r = api.get("/api/v1/places/detail/", {"id": "ChIJabcdefghij12345", "session": s})
    assert r.status_code == 200
    assert r.json() == {
        "direccion": "Avenida Larco 345", "distrito": "Miraflores", "provincia": "Lima", "departamento": "Lima",
        "formateada": "Av. Larco 345, Miraflores 15074, Perú", "lat": -12.1219, "lng": -77.0297,
    }
    pedido = google.llamadas[0]
    assert f"sessionToken={s}" in pedido["url"] and "ChIJabcdefghij12345" in pedido["url"]
    assert pedido["headers"]["X-Goog-FieldMask"] == "formattedAddress,addressComponents,location"


def test_el_detalle_rechaza_ids_raros_y_no_llega_a_google(api, google):
    for raro in ("../../etc/passwd", "a b", "x" * 300, ""):
        assert api.get("/api/v1/places/detail/", {"id": raro, "session": sesion()}).status_code == 400
    assert google.llamadas == []


def test_la_llave_secreta_nunca_sale_en_las_respuestas(api, google):
    google.respuesta = LUGAR_MIRAFLORES
    cuerpos = [
        api.get("/api/v1/store-settings/public/").content,
        api.get("/api/v1/places/detail/", {"id": "ChIJabcdefghij12345", "session": sesion()}).content,
    ]
    assert all(LLAVE.encode() not in c for c in cuerpos)


def test_ajustes_publicos_exponen_el_punto_de_recojo_y_el_mapa_solo_si_hay_direccion(api, settings):
    settings.GOOGLE_MAPS_EMBED_KEY = "llave-publica-del-mapa"
    cfg = StoreSettings.load()
    assert api.get("/api/v1/store-settings/public/").json()["mapa_embed_key"] == ""  # sin dirección no hay mapa
    cfg.punto_recojo_nombre = "Parque Kennedy"
    cfg.punto_recojo_direccion = "Parque Kennedy, Miraflores, Lima"
    cfg.save()
    data = api.get("/api/v1/store-settings/public/").json()
    assert data["mapa_embed_key"] == "llave-publica-del-mapa"
    assert data["punto_recojo_direccion"] == "Parque Kennedy, Miraflores, Lima"
