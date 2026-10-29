from rest_framework import mixins, serializers, viewsets
from rest_framework.generics import RetrieveAPIView
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.throttling import AnonRateThrottle

from .models import Order, OrderItem, OrderStatusHistory


class OrderItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = OrderItem
        fields = ("nombre_snapshot", "sku_snapshot", "precio_unitario", "cantidad")


class OrderHistorySerializer(serializers.ModelSerializer):
    class Meta:
        model = OrderStatusHistory
        fields = ("estado_nuevo", "creado_en")


class OrderSerializer(serializers.ModelSerializer):
    token = serializers.UUIDField(source="public_token", read_only=True)
    numero = serializers.IntegerField(source="id", read_only=True)
    items = OrderItemSerializer(many=True, read_only=True)
    historial = OrderHistorySerializer(many=True, read_only=True)

    class Meta:
        model = Order
        fields = (
            "numero", "token", "estado", "tipo_venta", "subtotal_pen", "envio_pen", "total_pen",
            "adelanto_pen", "saldo_pen", "metodo_entrega", "expira_en", "creado_en", "items", "historial",
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
            .prefetch_related("items", "historial")
            .order_by("-creado_en")
        )


class TrackOrderView(RetrieveAPIView):
    """Seguimiento de una invitada: el token UUID del pedido hace de secreto."""

    serializer_class = OrderSerializer
    permission_classes = [AllowAny]
    authentication_classes = []
    throttle_classes = [AnonRateThrottle]
    lookup_field = "public_token"
    queryset = Order.objects.prefetch_related("items", "historial")
