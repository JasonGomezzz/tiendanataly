from django.conf import settings

from .base import PaymentProvider
from .culqi import CulqiProvider
from .manual import ManualYapePlinProvider

_REGISTRY = {ManualYapePlinProvider.name: ManualYapePlinProvider, CulqiProvider.name: CulqiProvider}


def get_provider(name=None) -> PaymentProvider:
    """Devuelve el adaptador activo según el feature flag PAYMENTS_PROVIDER."""
    name = name or settings.PAYMENTS_PROVIDER
    try:
        return _REGISTRY[name]()
    except KeyError:
        raise NotImplementedError(f"Pasarela «{name}» no disponible todavía")
