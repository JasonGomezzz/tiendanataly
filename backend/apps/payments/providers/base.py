from abc import ABC, abstractmethod


class PaymentProvider(ABC):
    """Interfaz de pasarela. Cada adaptador (manual, Culqi, Izipay, Mercado Pago) la implementa.

    Reglas comunes: el monto sale siempre del pedido en el servidor, cada intento lleva una
    idempotency_key y el servidor nunca recibe ni guarda datos de tarjeta.
    """

    name: str

    @abstractmethod
    def create_payment(self, order, *, idempotency_key, **kwargs):
        """Crea (o devuelve, si la clave ya existe) el Payment del pedido."""

    def handle_webhook(self, body: bytes, headers: dict):
        raise NotImplementedError(f"{self.name} no recibe webhooks")
