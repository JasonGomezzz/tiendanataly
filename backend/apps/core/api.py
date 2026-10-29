from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_protect
from rest_framework import serializers
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.throttling import AnonRateThrottle, ScopedRateThrottle, UserRateThrottle
from rest_framework.views import APIView

from .models import StoreSettings


class CsrfProtectedMixin:
    """DRF solo exige CSRF a usuarios ya autenticados. Las vistas de login/registro la exigen
    siempre para evitar 'login CSRF' (que alguien meta a la víctima en otra cuenta)."""

    @method_decorator(csrf_protect)
    def dispatch(self, *args, **kwargs):
        return super().dispatch(*args, **kwargs)


class ScopedThrottleMixin:
    throttle_classes = [AnonRateThrottle, UserRateThrottle, ScopedRateThrottle]


class PublicStoreSettingsSerializer(serializers.ModelSerializer):
    class Meta:
        model = StoreSettings
        fields = (
            "nombre_tienda", "whatsapp", "aviso_legal", "costo_envio_default", "pct_adelanto",
            "minutos_reserva", "yape_numero", "yape_titular", "plin_numero", "plin_titular",
        )


class PublicStoreSettingsView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        return Response(PublicStoreSettingsSerializer(StoreSettings.load()).data)
