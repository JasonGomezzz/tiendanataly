from rest_framework import serializers, viewsets
from rest_framework.permissions import AllowAny

from .models import ShippingZone


class ShippingZoneSerializer(serializers.ModelSerializer):
    class Meta:
        model = ShippingZone
        fields = ("id", "nombre", "metodo", "costo", "courier", "instrucciones")


class ShippingZoneViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = ShippingZone.objects.filter(activa=True)
    serializer_class = ShippingZoneSerializer
    permission_classes = [AllowAny]
    pagination_class = None
    filter_backends = []
