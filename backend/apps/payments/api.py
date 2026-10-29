import base64
import hmac
import uuid

from django.conf import settings
from django.shortcuts import get_object_or_404
from rest_framework import serializers, status
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.core.api import CsrfProtectedMixin, ScopedThrottleMixin
from apps.core.validators import validate_image_file
from apps.integrations.services import enqueue
from apps.orders.models import Order

from .models import Payment
from .providers import get_provider
from .providers.culqi_client import CulqiError
from .services import PaymentError
from .webhooks import InvalidEvent, process_event


class ManualPaymentSerializer(serializers.Serializer):
    comprobante = serializers.ImageField(validators=[validate_image_file])
    metodo = serializers.ChoiceField(choices=[Payment.Metodo.YAPE, Payment.Metodo.PLIN])
    idempotency_key = serializers.CharField(max_length=60, required=False)


class ManualPaymentView(CsrfProtectedMixin, ScopedThrottleMixin, APIView):
    """La clienta sube la captura de su Yape/Plin; la administradora la verifica a mano."""

    permission_classes = [AllowAny]
    parser_classes = [MultiPartParser, FormParser]
    throttle_scope = "checkout"

    def post(self, request, public_token):
        order = get_object_or_404(Order, public_token=public_token)
        if order.amount_due() <= 0:
            return Response({"detail": "Este pedido ya no admite pagos."}, status=status.HTTP_409_CONFLICT)
        s = ManualPaymentSerializer(data=request.data)
        s.is_valid(raise_exception=True)
        key = f"{order.pk}:{s.validated_data.get('idempotency_key') or uuid.uuid4().hex}"
        # El monto lo define el servidor a partir del pedido; el cliente no lo envía.
        payment = get_provider("manual_yape_plin").create_payment(
            order, idempotency_key=key, metodo=s.validated_data["metodo"], comprobante=s.validated_data["comprobante"],
        )
        enqueue("payment.proof_uploaded", {"pedido": order.pk, "pago": payment.pk, "monto": str(payment.monto)})
        return Response({"estado": payment.estado, "monto": str(payment.monto)}, status=status.HTTP_201_CREATED)


# --- Culqi -------------------------------------------------------------------

class CulqiChargeSerializer(serializers.Serializer):
    token_id = serializers.CharField(max_length=80)  # lo genera Culqi Checkout en el navegador (SAQ-A)
    email = serializers.EmailField(required=False, allow_blank=True, default="")
    idempotency_key = serializers.CharField(max_length=60)


class CulqiOrderSerializer(serializers.Serializer):
    email = serializers.EmailField(required=False, allow_blank=True, default="")
    idempotency_key = serializers.CharField(max_length=60)


class CulqiBase(CsrfProtectedMixin, ScopedThrottleMixin, APIView):
    permission_classes = [AllowAny]
    throttle_scope = "checkout"

    def get_order(self, public_token):
        order = get_object_or_404(Order, public_token=public_token)
        if order.amount_due() <= 0:
            return None, Response({"detail": "Este pedido ya no admite pagos."}, status=status.HTTP_409_CONFLICT)
        if not settings.CULQI_SECRET_KEY:
            return None, Response({"detail": "El pago con tarjeta no está disponible."}, status=status.HTTP_503_SERVICE_UNAVAILABLE)
        return order, None


class CulqiChargeView(CulqiBase):
    """Cobra con tarjeta. El monto lo calcula el servidor; el cliente solo envía el token de Culqi."""

    def post(self, request, public_token):
        order, error = self.get_order(public_token)
        if error:
            return error
        s = CulqiChargeSerializer(data=request.data)
        s.is_valid(raise_exception=True)
        key = f"{order.pk}:{s.validated_data['idempotency_key']}"
        try:
            payment = get_provider("culqi").create_payment(order, idempotency_key=key, token_id=s.validated_data["token_id"], email=s.validated_data["email"])
        except PaymentError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_409_CONFLICT)
        order.refresh_from_db()
        body = {"estado": payment.estado, "pedido_estado": order.estado}
        if payment.estado == Payment.Estado.RECHAZADO:
            body["detail"] = payment.nota or "No pudimos procesar el pago."
            return Response(body, status=status.HTTP_402_PAYMENT_REQUIRED)
        return Response(body, status=status.HTTP_201_CREATED)


class CulqiOrderView(CulqiBase):
    """Crea la orden de pago de Culqi (billeteras/PagoEfectivo). El pago se confirma por webhook."""

    def post(self, request, public_token):
        order, error = self.get_order(public_token)
        if error:
            return error
        s = CulqiOrderSerializer(data=request.data)
        s.is_valid(raise_exception=True)
        key = f"{order.pk}:order:{s.validated_data['idempotency_key']}"
        try:
            payment = get_provider("culqi").create_order(order, idempotency_key=key, email=s.validated_data["email"])
        except CulqiError as exc:
            return Response({"detail": exc.user_message}, status=status.HTTP_502_BAD_GATEWAY)
        return Response({"culqi_order_id": payment.external_id, "monto": str(payment.monto)}, status=status.HTTP_201_CREATED)


class CulqiWebhookView(APIView):
    """Recibe eventos de Culqi. Ver apps/payments/webhooks.py para el modelo de seguridad."""

    permission_classes = [AllowAny]
    authentication_classes = []
    throttle_classes = []

    def _authorized(self, request, secret):
        expected = settings.CULQI_WEBHOOK_SECRET
        if not expected or not hmac.compare_digest(secret.encode(), expected.encode()):
            return False
        user, password = settings.CULQI_WEBHOOK_BASIC_USER, settings.CULQI_WEBHOOK_BASIC_PASSWORD
        if user or password:
            header = request.META.get("HTTP_AUTHORIZATION", "")
            try:
                scheme, encoded = header.split(" ", 1)
                got_user, _, got_password = base64.b64decode(encoded).decode().partition(":")
            except (ValueError, UnicodeDecodeError):
                return False
            return (
                scheme.lower() == "basic"
                and hmac.compare_digest(got_user.encode(), user.encode())
                and hmac.compare_digest(got_password.encode(), password.encode())
            )
        return True

    def post(self, request, secret):
        if not self._authorized(request, secret):
            return Response(status=status.HTTP_404_NOT_FOUND)  # no revela que el endpoint existe
        try:
            result = process_event(request.data if isinstance(request.data, dict) else {})
        except InvalidEvent:
            return Response({"detail": "evento inválido"}, status=status.HTTP_400_BAD_REQUEST)
        except CulqiError:
            return Response({"detail": "reintentar"}, status=status.HTTP_503_SERVICE_UNAVAILABLE)  # Culqi reintenta
        return Response({"resultado": result})
