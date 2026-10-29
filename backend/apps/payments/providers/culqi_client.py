"""Cliente HTTP mínimo de Culqi (sin dependencias nuevas).

Verificado en la documentación oficial: llaves pública/secreta, el token de Checkout se envía al backend
como `source_id` para crear el cargo, y el evento `order.status.changed` confirma órdenes de pago.

NO verificado (la documentación pública no carga en este entorno): URL base de la API, unidad del monto
(aquí céntimos, como indica la convención de Culqi) y nombres exactos de algunos campos. Todo está
concentrado en este archivo y en settings.CULQI_API_BASE para ajustarlo con llaves de sandbox.
"""
import json
import urllib.error
import urllib.request

from django.conf import settings


class CulqiError(Exception):
    def __init__(self, message, *, status=0, body=None):
        super().__init__(message)
        self.status = status
        self.body = body or {}

    @property
    def user_message(self):
        return str(self.body.get("user_message") or self.body.get("merchant_message") or "No pudimos procesar el pago.")


class CulqiClient:
    def __init__(self, secret_key=None, base_url=None, opener=None):
        self.secret_key = secret_key or settings.CULQI_SECRET_KEY
        self.base_url = (base_url or settings.CULQI_API_BASE).rstrip("/")
        self._open = opener or urllib.request.urlopen

    def _request(self, method, path, payload=None):
        if not self.secret_key:
            raise CulqiError("Culqi no está configurado (falta CULQI_SECRET_KEY).")
        req = urllib.request.Request(
            f"{self.base_url}{path}",
            data=json.dumps(payload).encode() if payload is not None else None,
            method=method,
            headers={"Authorization": f"Bearer {self.secret_key}", "Content-Type": "application/json"},
        )
        try:
            with self._open(req, timeout=15) as resp:
                return json.loads(resp.read().decode() or "{}")
        except urllib.error.HTTPError as exc:
            try:
                body = json.loads(exc.read().decode() or "{}")
            except ValueError:
                body = {}
            raise CulqiError(f"Culqi respondió {exc.code}", status=exc.code, body=body) from exc
        except (urllib.error.URLError, TimeoutError, OSError) as exc:
            raise CulqiError("No se pudo contactar a Culqi.", status=0) from exc

    def create_charge(self, payload):
        return self._request("POST", "/charges", payload)

    def get_charge(self, charge_id):
        return self._request("GET", f"/charges/{charge_id}")

    def create_order(self, payload):
        return self._request("POST", "/orders", payload)

    def get_order(self, order_id):
        return self._request("GET", f"/orders/{order_id}")
