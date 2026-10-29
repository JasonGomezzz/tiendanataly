import django_filters
from django.db.models import Avg, F, OuterRef, Subquery, Sum
from django.db.models.functions import Coalesce
from rest_framework import serializers, status, viewsets
from rest_framework.decorators import action
from rest_framework.generics import CreateAPIView, get_object_or_404
from rest_framework.pagination import PageNumberPagination
from rest_framework.permissions import AllowAny, IsAuthenticatedOrReadOnly
from rest_framework.response import Response

from apps.core.api import ScopedThrottleMixin

from .models import Brand, Category, Collection, Product, ProductImage, ProductVariant, Review, StockAlert

LAST_UNITS_THRESHOLD = 2


class BrandSerializer(serializers.ModelSerializer):
    class Meta:
        model = Brand
        fields = ("nombre", "slug")


class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = ("nombre", "slug")


class ImageSerializer(serializers.ModelSerializer):
    url = serializers.SerializerMethodField()

    class Meta:
        model = ProductImage
        fields = ("url", "alt", "orden")

    def get_url(self, obj):
        # URL relativa (/media/...): el navegador la pide a Next, que la reenvía al backend.
        return obj.imagen.url


class VariantSerializer(serializers.ModelSerializer):
    disponible = serializers.IntegerField(read_only=True)
    agotado = serializers.SerializerMethodField()

    class Meta:
        model = ProductVariant
        fields = ("id", "sku", "nombre", "atributo", "disponible", "agotado")

    def get_agotado(self, obj):
        return obj.disponible <= 0


class ProductListSerializer(serializers.ModelSerializer):
    marca = BrandSerializer(read_only=True)
    categoria = CategorySerializer(read_only=True)
    imagen_principal = serializers.SerializerMethodField()
    stock = serializers.SerializerMethodField()
    ultimas_unidades = serializers.SerializerMethodField()
    agotado = serializers.SerializerMethodField()

    class Meta:
        model = Product
        fields = ("slug", "nombre", "marca", "categoria", "linea", "tipo_venta", "precio_venta_pen", "imagen_principal", "stock", "ultimas_unidades", "agotado")

    def _stock(self, obj):
        if obj.tipo_venta == Product.TipoVenta.POR_ENCARGO:
            return 99
        return sum(max(v.disponible, 0) for v in obj.variantes.all() if v.activo)

    def get_stock(self, obj):
        return self._stock(obj)

    def get_agotado(self, obj):
        return self._stock(obj) <= 0

    def get_ultimas_unidades(self, obj):
        return 0 < self._stock(obj) <= LAST_UNITS_THRESHOLD

    def get_imagen_principal(self, obj):
        images = list(obj.imagenes.all())
        if not images:
            return None
        return images[0].imagen.url


class ProductDetailSerializer(ProductListSerializer):
    imagenes = ImageSerializer(many=True, read_only=True)
    variantes = serializers.SerializerMethodField()
    puntaje_promedio = serializers.SerializerMethodField()

    class Meta(ProductListSerializer.Meta):
        fields = ProductListSerializer.Meta.fields + ("descripcion", "detalles", "imagenes", "variantes", "puntaje_promedio")

    def get_variantes(self, obj):
        return VariantSerializer([v for v in obj.variantes.all() if v.activo], many=True).data

    def get_puntaje_promedio(self, obj):
        avg = obj.resenas.filter(estado=Review.Estado.APROBADA).aggregate(a=Avg("puntaje"))["a"]
        return round(avg, 1) if avg else None


class ReviewSerializer(serializers.ModelSerializer):
    class Meta:
        model = Review
        fields = ("autor", "puntaje", "comentario", "foto", "creado_en")
        read_only_fields = ("creado_en",)


class ProductFilter(django_filters.FilterSet):
    categoria = django_filters.CharFilter(field_name="categoria__slug")
    marca = django_filters.CharFilter(field_name="marca__slug")
    coleccion = django_filters.CharFilter(field_name="colecciones__slug")
    precio_min = django_filters.NumberFilter(field_name="precio_venta_pen", lookup_expr="gte")
    precio_max = django_filters.NumberFilter(field_name="precio_venta_pen", lookup_expr="lte")
    disponible = django_filters.BooleanFilter(method="filter_disponible")
    ultimas = django_filters.BooleanFilter(method="filter_ultimas")

    class Meta:
        model = Product
        fields = ["categoria", "marca", "coleccion", "precio_min", "precio_max", "disponible", "ultimas"]

    def filter_disponible(self, queryset, name, value):
        return queryset.filter(stock_libre__gt=0) if value else queryset.filter(stock_libre__lte=0)

    def filter_ultimas(self, queryset, name, value):
        low = queryset.filter(stock_libre__gt=0, stock_libre__lte=LAST_UNITS_THRESHOLD)
        return low if value else queryset.exclude(pk__in=low.values("pk"))


class CatalogPagination(PageNumberPagination):
    page_size = 24
    page_size_query_param = "page_size"
    max_page_size = 200


class ProductViewSet(viewsets.ReadOnlyModelViewSet):
    """Catálogo público: solo productos publicados o agotados con precio. Nunca expone costos."""

    permission_classes = [AllowAny]
    pagination_class = CatalogPagination
    lookup_field = "slug"
    filterset_class = ProductFilter
    search_fields = ["nombre", "descripcion", "marca__nombre", "linea"]
    ordering_fields = ["precio_venta_pen", "orden", "creado_en"]
    ordering = ["orden", "nombre"]

    def get_queryset(self):
        libre = (
            ProductVariant.objects.filter(producto=OuterRef("pk"), activo=True)
            .values("producto")
            .annotate(total=Sum(F("stock_disponible") - F("stock_reservado")))
            .values("total")
        )
        return (
            Product.objects.filter(estado__in=[Product.Estado.PUBLICADO, Product.Estado.AGOTADO], precio_venta_pen__isnull=False)
            .annotate(stock_libre=Coalesce(Subquery(libre), 0))
            .select_related("marca", "categoria")
            .prefetch_related("imagenes", "variantes")
        )

    def get_serializer_class(self):
        return ProductDetailSerializer if self.action == "retrieve" else ProductListSerializer

    @action(detail=True, methods=["get"], filter_backends=[], pagination_class=None)
    def related(self, request, slug=None):
        """"Completa tu look": otros productos de la misma categoría."""
        product = self.get_object()
        qs = self.get_queryset().filter(categoria=product.categoria).exclude(pk=product.pk).order_by("-stock_libre", "orden")[:4]
        return Response(ProductListSerializer(qs, many=True, context={"request": request}).data)

    @action(detail=True, methods=["get", "post"], permission_classes=[IsAuthenticatedOrReadOnly], filter_backends=[], pagination_class=None)
    def reviews(self, request, slug=None):
        product = self.get_object()
        if request.method == "GET":
            qs = product.resenas.filter(estado=Review.Estado.APROBADA)
            return Response(ReviewSerializer(qs, many=True, context={"request": request}).data)
        s = ReviewSerializer(data=request.data)
        s.is_valid(raise_exception=True)
        customer = getattr(request.user, "customer", None)
        s.save(producto=product, cliente=customer, estado=Review.Estado.PENDIENTE)  # siempre moderada
        return Response({"detail": "¡Gracias! Tu reseña será publicada tras la revisión."}, status=status.HTTP_201_CREATED)


class CategoryViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Category.objects.all()
    serializer_class = CategorySerializer
    permission_classes = [AllowAny]
    lookup_field = "slug"
    pagination_class = None
    filter_backends = []


class BrandViewSet(CategoryViewSet):
    queryset = Brand.objects.all()
    serializer_class = BrandSerializer


class CollectionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Collection
        fields = ("nombre", "slug", "descripcion")


class CollectionViewSet(CategoryViewSet):
    queryset = Collection.objects.filter(activa=True)
    serializer_class = CollectionSerializer


class StockAlertSerializer(serializers.ModelSerializer):
    class Meta:
        model = StockAlert
        fields = ("email", "telefono")

    def validate(self, attrs):
        if not attrs.get("email") and not attrs.get("telefono"):
            raise serializers.ValidationError("Indica un correo o un teléfono para avisarte.")
        return attrs


class StockAlertCreateView(ScopedThrottleMixin, CreateAPIView):
    permission_classes = [AllowAny]
    serializer_class = StockAlertSerializer
    throttle_scope = "complaint"

    def perform_create(self, serializer):
        variant = get_object_or_404(
            ProductVariant, pk=self.kwargs["variant_id"], activo=True,
            producto__estado__in=[Product.Estado.PUBLICADO, Product.Estado.AGOTADO],
        )
        serializer.save(variante=variant)
