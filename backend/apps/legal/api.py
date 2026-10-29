from rest_framework import serializers
from rest_framework.generics import CreateAPIView
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

from apps.core.api import ScopedThrottleMixin

from .models import Complaint


class ComplaintSerializer(serializers.ModelSerializer):
    class Meta:
        model = Complaint
        fields = (
            "nombre", "doc_tipo", "doc_numero", "domicilio", "telefono", "email", "es_menor", "apoderado",
            "bien", "monto_reclamado", "descripcion_bien", "pedido_ref", "tipo", "detalle", "pedido_consumidor",
        )

    def validate(self, attrs):
        if attrs.get("es_menor") and not attrs.get("apoderado"):
            raise serializers.ValidationError({"apoderado": "Indica el nombre del padre, madre o apoderado."})
        return attrs


class ComplaintCreateView(ScopedThrottleMixin, CreateAPIView):
    """Libro de Reclamaciones virtual: público, con límite de envíos por hora."""

    permission_classes = [AllowAny]
    authentication_classes = []
    serializer_class = ComplaintSerializer
    throttle_scope = "complaint"

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        complaint = serializer.save()
        return Response({"correlativo": complaint.correlativo}, status=201)
