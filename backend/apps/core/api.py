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
    payments_provider = serializers.SerializerMethodField()
    culqi_public_key = serializers.SerializerMethodField()
    cuentas = serializers.SerializerMethodField()

    def get_cuentas(self, obj):
        from apps.payments.models import BankAccount

        return list(BankAccount.objects.filter(activa=True).values("id", "banco", "etiqueta", "numero", "cci", "titular"))

    def get_payments_provider(self, obj):
        from django.conf import settings

        # Culqi solo se ofrece si está activado por feature flag Y hay llaves configuradas.
        ok = settings.PAYMENTS_PROVIDER == "culqi" and settings.CULQI_PUBLIC_KEY and settings.CULQI_SECRET_KEY
        return "culqi" if ok else "manual_yape_plin"

    def get_culqi_public_key(self, obj):
        from django.conf import settings

        return settings.CULQI_PUBLIC_KEY if self.get_payments_provider(obj) == "culqi" else ""

    class Meta:
        model = StoreSettings
        fields = (
            "nombre_tienda", "whatsapp", "aviso_legal", "costo_envio_default", "pct_adelanto",
            "minutos_reserva", "yape_numero", "yape_titular", "plin_numero", "plin_titular", "payments_provider", "culqi_public_key", "cuentas",
        )


class PublicStoreSettingsView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        return Response(PublicStoreSettingsSerializer(StoreSettings.load()).data)
