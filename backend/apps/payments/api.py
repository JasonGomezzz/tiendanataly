import uuid

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
        if order.estado != Order.Estado.PENDIENTE_PAGO:
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
