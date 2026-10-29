from django.shortcuts import get_object_or_404
from rest_framework import mixins, serializers, status, viewsets
from rest_framework.generics import RetrieveAPIView
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.throttling import AnonRateThrottle
from rest_framework.views import APIView

from apps.cart.api import get_cart
from apps.core.api import CsrfProtectedMixin, ScopedThrottleMixin
from apps.payments.models import Payment
from apps.shipping.models import ShippingZone

from .checkout import CheckoutError, create_order_from_cart
from .models import Order, OrderItem, OrderStatusHistory
from .whatsapp import order_whatsapp


class OrderItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = OrderItem
        fields = ("nombre_snapshot", "sku_snapshot", "precio_unitario", "cantidad")


class OrderHistorySerializer(serializers.ModelSerializer):
    class Meta:
        model = OrderStatusHistory
        fields = ("estado_nuevo", "creado_en")


class OrderPaymentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Payment
        fields = ("metodo", "monto", "estado", "es_adelanto", "creado_en")


class OrderSerializer(serializers.ModelSerializer):
    token = serializers.UUIDField(source="public_token", read_only=True)
    numero = serializers.IntegerField(source="id", read_only=True)
    items = OrderItemSerializer(many=True, read_only=True)
    historial = OrderHistorySerializer(many=True, read_only=True)
    pagos = OrderPaymentSerializer(many=True, read_only=True)
    monto_a_cobrar = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True)
    por_pagar = serializers.DecimalField(source="amount_due", max_digits=10, decimal_places=2, read_only=True)

    class Meta:
        model = Order
        fields = (
            "numero", "token", "estado", "tipo_venta", "subtotal_pen", "envio_pen", "total_pen", "adelanto_pen", "saldo_pen",
            "monto_a_cobrar", "por_pagar", "metodo_entrega", "expira_en", "creado_en", "items", "historial", "pagos",
        )


class MyOrderViewSet(mixins.ListModelMixin, mixins.RetrieveModelMixin, viewsets.GenericViewSet):
    """Pedidos de la clienta autenticada. El queryset se filtra por propietaria (sin IDOR)."""

    serializer_class = OrderSerializer
    permission_classes = [IsAuthenticated]
    lookup_field = "public_token"
    filter_backends = []

    def get_queryset(self):
        return (
            Order.objects.filter(cliente__user=self.request.user)
            .prefetch_related("items", "historial", "pagos")
            .order_by("-creado_en")
        )


class TrackOrderView(RetrieveAPIView):
    """Seguimiento de una invitada: el token UUID del pedido hace de secreto."""

    serializer_class = OrderSerializer
    permission_classes = [AllowAny]
    authentication_classes = []
    throttle_classes = [AnonRateThrottle]
    lookup_field = "public_token"
    queryset = Order.objects.prefetch_related("items", "historial", "pagos")


class OrderWhatsappView(RetrieveAPIView):
    permission_classes = [AllowAny]
    authentication_classes = []
    throttle_classes = [AnonRateThrottle]

    def get(self, request, public_token):
        order = get_object_or_404(Order.objects.prefetch_related("items").select_related("cliente"), public_token=public_token)
        return Response(order_whatsapp(order))


class AddressDataSerializer(serializers.Serializer):
    departamento = serializers.CharField(max_length=60)
    provincia = serializers.CharField(max_length=60)
    distrito = serializers.CharField(max_length=60)
    direccion = serializers.CharField(max_length=255)
    referencia = serializers.CharField(max_length=255, required=False, allow_blank=True, default="")


class CheckoutSerializer(serializers.Serializer):
    nombre = serializers.CharField(max_length=120)
    telefono = serializers.RegexField(r"^\+?[0-9 ]{7,15}$", max_length=20, error_messages={"invalid": "Ingresa un teléfono válido."})
    email = serializers.EmailField(required=False, allow_blank=True, default="")
    metodo_entrega = serializers.ChoiceField(choices=Order.Entrega.choices)
    zona_id = serializers.IntegerField()
    direccion = AddressDataSerializer(required=False)
    notas = serializers.CharField(max_length=500, required=False, allow_blank=True, default="")
    doc_tipo = serializers.ChoiceField(choices=["DNI", "RUC"], required=False, allow_blank=True, default="")
    doc_numero = serializers.CharField(max_length=15, required=False, allow_blank=True, default="")
    acepta_privacidad = serializers.BooleanField()
    acepta_terminos = serializers.BooleanField()
    acepta_marketing = serializers.BooleanField(required=False, default=False)

    def validate_acepta_privacidad(self, value):
        if not value:
            raise serializers.ValidationError("Debes aceptar la política de privacidad.")
        return value

    def validate_acepta_terminos(self, value):
        if not value:
            raise serializers.ValidationError("Debes aceptar los términos y condiciones.")
        return value

    def validate(self, attrs):
        if attrs["metodo_entrega"] != Order.Entrega.RECOJO and not attrs.get("direccion"):
            raise serializers.ValidationError({"direccion": "Indica la dirección de entrega."})
        return attrs


class CheckoutView(CsrfProtectedMixin, ScopedThrottleMixin, APIView):
    permission_classes = [AllowAny]
    throttle_scope = "checkout"

    def post(self, request):
        s = CheckoutSerializer(data=request.data)
        s.is_valid(raise_exception=True)
        cart = get_cart(request)
        try:
            order = create_order_from_cart(cart, s.validated_data, user=request.user, ip=request.META.get("REMOTE_ADDR"))
        except CheckoutError as exc:
            return Response({"detail": str(exc), "code": exc.code}, status=exc.status)
        order = Order.objects.prefetch_related("items", "historial", "pagos").get(pk=order.pk)
        return Response({**OrderSerializer(order).data, "whatsapp": order_whatsapp(order)}, status=status.HTTP_201_CREATED)
