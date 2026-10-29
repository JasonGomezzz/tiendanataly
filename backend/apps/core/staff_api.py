"""API interna del panel /admin (Next.js). Toda la autorización se valida aquí, nunca en el frontend.

- Solo cuentas `is_staff` con rol Administradora o Staff (o el superusuario técnico).
- Con ADMIN_REQUIRE_2FA la sesión debe estar verificada con TOTP.
- Cada vista exige permisos de Django por método (los mismos del admin de Django), así que Staff
  no ve costos, pagos, configuración ni auditoría.
- Toda escritura queda en AuditLog.
"""
from datetime import timedelta
from decimal import Decimal

from django.conf import settings
from django.db import transaction
from django.db.models import Count, F, Q, Sum
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.utils.text import slugify
from rest_framework import serializers, status
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.permissions import BasePermission
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.catalog.models import Brand, Category, Collection, Product, ProductImage, ProductVariant
from apps.core.audit import log_action
from apps.core.models import AuditLog, ExchangeRate, StoreSettings
from apps.core.roles import ADMINISTRADORA, STAFF
from apps.core.validators import validate_image_file
from apps.inventory import services as stock
from apps.orders import services as order_services
from apps.orders.models import Order
from apps.payments import services as payment_services
from apps.payments.models import Payment
from apps.pricing.services import PricingError, calculate_price

LOW_STOCK = 1


class IsStaffRole(BasePermission):
    def has_permission(self, request, view):
        u = request.user
        if not (u and u.is_authenticated and u.is_active and u.is_staff):
            return False
        if not (u.is_superuser or u.groups.filter(name__in=[ADMINISTRADORA, STAFF]).exists()):
            return False
        if settings.ADMIN_REQUIRE_2FA and not getattr(u, "is_verified", lambda: False)():
            return False
        return True


class MethodPerms(BasePermission):
    """Cada vista declara `perm_map = {"GET": [...], "POST": [...]}` con permisos de Django."""

    def has_permission(self, request, view):
        needed = getattr(view, "perm_map", {}).get(request.method)
        if needed is None:
            return False  # método sin permiso declarado = no permitido
        return all(request.user.has_perm(p) for p in needed)


class StaffView(APIView):
    permission_classes = [IsStaffRole, MethodPerms]
    perm_map: dict = {}


def can_see_finance(user):
    return user.has_perm("catalog.ver_finanzas")


def audit(request, kind, obj, **cambios):
    log_action(request, kind, obj, cambios=cambios)


# --- Meta -------------------------------------------------------------------

class MeStaffView(StaffView):
    perm_map = {"GET": []}

    def get(self, request):
        u = request.user
        perms = ["catalog.add_product", "catalog.change_product", "catalog.ver_finanzas", "payments.view_payment", "payments.change_payment", "core.change_storesettings", "core.view_auditlog", "core.add_exchangerate", "orders.change_order"]
        return Response({
            "id": u.pk, "email": u.email, "nombre": u.get_full_name() or u.get_username(),
            "rol": "superusuario" if u.is_superuser else ("administradora" if u.groups.filter(name=ADMINISTRADORA).exists() else "staff"),
            "permisos": {p: u.has_perm(p) for p in perms},
        })


class MetaView(StaffView):
    perm_map = {"GET": ["catalog.view_product"]}

    def get(self, request):
        return Response({
            "marcas": list(Brand.objects.values("id", "nombre")),
            "categorias": list(Category.objects.values("id", "nombre")),
            "colecciones": list(Collection.objects.values("id", "nombre")),
            "estados_producto": [{"value": v, "label": l} for v, l in Product.Estado.choices],
            "tipos_venta": [{"value": v, "label": l} for v, l in Product.TipoVenta.choices],
            "estados_pedido": [{"value": v, "label": l} for v, l in Order.Estado.choices],
            "tipos_variante": [{"value": v, "label": l} for v, l in ProductVariant.Atributo.choices],
            "transiciones": {k.value if hasattr(k, "value") else k: sorted(getattr(x, "value", x) for x in v) for k, v in order_services.ALLOWED_TRANSITIONS.items()},
        })


# --- Dashboard --------------------------------------------------------------

class DashboardView(StaffView):
    perm_map = {"GET": ["orders.view_order"]}

    def get(self, request):
        today = timezone.localdate()
        tz = timezone.get_current_timezone()
        start = timezone.make_aware(timezone.datetime.combine(today, timezone.datetime.min.time()), tz)
        orders = Order.objects.all()
        por_estado = dict(orders.values_list("estado").annotate(n=Count("id")))
        low = (
            ProductVariant.objects.filter(activo=True, producto__estado__in=["publicado", "agotado"], producto__tipo_venta="stock_local")
            .annotate(libre=F("stock_disponible") - F("stock_reservado"))
            .filter(libre__lte=LOW_STOCK)
            .select_related("producto")
            .order_by("libre", "producto__nombre")[:12]
        )
        data = {
            "pedidos_hoy": orders.filter(creado_en__gte=start).count(),
            "por_estado": por_estado,
            "por_comprar": orders.filter(estado=Order.Estado.PAGADO, tipo_venta="por_encargo").count(),
            "por_entregar": orders.filter(estado__in=[Order.Estado.PAGADO, Order.Estado.EN_LIMA], tipo_venta="stock_local").count()
            + orders.filter(estado=Order.Estado.EN_LIMA, tipo_venta="por_encargo").count(),
            "stock_bajo": [{"id": v.pk, "producto_id": v.producto_id, "producto": v.producto.nombre, "variante": v.nombre, "libre": max(v.libre, 0)} for v in low],
        }
        if request.user.has_perm("payments.view_payment"):
            data["pagos_en_revision"] = Payment.objects.filter(estado=Payment.Estado.EN_REVISION).count()
        if can_see_finance(request.user):
            approved = Payment.objects.filter(estado=Payment.Estado.APROBADO)
            data["ventas_hoy"] = str(approved.filter(revisado_en__gte=start).aggregate(t=Sum("monto"))["t"] or Decimal("0"))
            week = []
            for i in range(6, -1, -1):
                day = today - timedelta(days=i)
                lo = timezone.make_aware(timezone.datetime.combine(day, timezone.datetime.min.time()), tz)
                total = approved.filter(revisado_en__gte=lo, revisado_en__lt=lo + timedelta(days=1)).aggregate(t=Sum("monto"))["t"] or Decimal("0")
                week.append({"fecha": day.isoformat(), "total": str(total)})
            data["ventas_semana"] = week
            data["ventas_mes"] = str(approved.filter(revisado_en__gte=start.replace(day=1)).aggregate(t=Sum("monto"))["t"] or Decimal("0"))
        return Response(data)


# --- Productos ---------------------------------------------------------------

FINANCE_FIELDS = ("precio_compra_usd", "margen", "precio_venta_pen", "oferta_cantidad", "oferta_precio")


class AdminVariantSerializer(serializers.ModelSerializer):
    libre = serializers.IntegerField(source="disponible", read_only=True)

    class Meta:
        model = ProductVariant
        fields = ("id", "sku", "nombre", "atributo", "activo", "stock_disponible", "stock_reservado", "libre")
        read_only_fields = ("stock_disponible", "stock_reservado")


class AdminImageSerializer(serializers.ModelSerializer):
    url = serializers.SerializerMethodField()

    def get_url(self, obj):
        return obj.imagen.url

    class Meta:
        model = ProductImage
        fields = ("id", "url", "alt", "orden")


class AdminProductSerializer(serializers.ModelSerializer):
    variantes = AdminVariantSerializer(many=True, read_only=True)
    imagenes = AdminImageSerializer(many=True, read_only=True)
    stock_total = serializers.IntegerField(source="stock_total_disponible", read_only=True)
    marca_nombre = serializers.CharField(source="marca.nombre", read_only=True)
    categoria_nombre = serializers.CharField(source="categoria.nombre", read_only=True)
    slug = serializers.SlugField(required=False)

    class Meta:
        model = Product
        fields = (
            "id", "nombre", "slug", "marca", "marca_nombre", "categoria", "categoria_nombre", "linea", "descripcion", "detalles",
            "estado", "tipo_venta", "orden", "notas_internas", "precio_compra_usd", "margen", "precio_venta_pen", "oferta_cantidad", "oferta_precio",
            "stock_total", "variantes", "imagenes",
        )

    def to_representation(self, instance):
        data = super().to_representation(instance)
        if not can_see_finance(self.context["request"].user):
            for f in FINANCE_FIELDS:
                data.pop(f, None)
        return data

    def validate(self, attrs):
        if not can_see_finance(self.context["request"].user):
            for f in FINANCE_FIELDS:  # sin permiso se ignoran en silencio
                attrs.pop(f, None)
        from apps.pricing.promos import validate_offer

        price = attrs.get("precio_venta_pen", getattr(self.instance, "precio_venta_pen", None))
        qty = attrs.get("oferta_cantidad", getattr(self.instance, "oferta_cantidad", None))
        offer = attrs.get("oferta_precio", getattr(self.instance, "oferta_precio", None))
        error = validate_offer(price, qty, offer)
        if error:
            raise serializers.ValidationError({"oferta_precio": error})
        estado = attrs.get("estado")
        if estado in (Product.Estado.PUBLICADO, Product.Estado.AGOTADO):
            price = attrs.get("precio_venta_pen", getattr(self.instance, "precio_venta_pen", None))
            if not price:
                raise serializers.ValidationError({"estado": "Para publicar, primero define el precio de venta."})
        return attrs


def unique_slug(name, exclude=None):
    base = slugify(name)[:150] or "producto"
    slug, n = base, 2
    qs = Product.objects.all() if exclude is None else Product.objects.exclude(pk=exclude)
    while qs.filter(slug=slug).exists():
        slug, n = f"{base}-{n}", n + 1
    return slug


class ProductListView(StaffView):
    perm_map = {"GET": ["catalog.view_product"], "POST": ["catalog.add_product"]}

    def get(self, request):
        qs = Product.objects.select_related("marca", "categoria").prefetch_related("variantes", "imagenes")
        q, estado = request.query_params.get("q"), request.query_params.get("estado")
        if q:
            qs = qs.filter(Q(nombre__icontains=q) | Q(slug__icontains=q) | Q(variantes__sku__icontains=q)).distinct()
        if estado:
            qs = qs.filter(estado=estado)
        return Response(AdminProductSerializer(qs[:200], many=True, context={"request": request}).data)

    @transaction.atomic
    def post(self, request):
        variants = request.data.get("variantes") or []
        s = AdminProductSerializer(data={k: v for k, v in request.data.items() if k != "variantes"}, context={"request": request})
        s.is_valid(raise_exception=True)
        slug = s.validated_data.get("slug") or unique_slug(s.validated_data["nombre"])
        product = s.save(slug=slug, estado=Product.Estado.BORRADOR if not s.validated_data.get("precio_venta_pen") else s.validated_data.get("estado", Product.Estado.BORRADOR))
        for i, v in enumerate(variants or [{"nombre": "Única", "atributo": "unico", "stock": 0}]):
            variant = ProductVariant.objects.create(
                producto=product, sku=f"{slugify(product.slug).upper()[:30]}-{i + 1}", nombre=v.get("nombre") or "Única", atributo=v.get("atributo") or "unico",
            )
            units = int(v.get("stock") or 0)
            if units > 0:
                stock.add_stock(variant, units, "Stock inicial", user=request.user)
        audit(request, AuditLog.Accion.CREAR, product)
        return Response(AdminProductSerializer(Product.objects.get(pk=product.pk), context={"request": request}).data, status=status.HTTP_201_CREATED)


class ProductDetailView(StaffView):
    perm_map = {"GET": ["catalog.view_product"], "PATCH": ["catalog.change_product"]}

    def get(self, request, pk):
        return Response(AdminProductSerializer(get_object_or_404(Product, pk=pk), context={"request": request}).data)

    def patch(self, request, pk):
        product = get_object_or_404(Product, pk=pk)
        s = AdminProductSerializer(product, data=request.data, partial=True, context={"request": request})
        s.is_valid(raise_exception=True)
        s.save()
        audit(request, AuditLog.Accion.EDITAR, product, campos=sorted(s.validated_data.keys()))
        return Response(AdminProductSerializer(Product.objects.get(pk=pk), context={"request": request}).data)


class ProductStateView(StaffView):
    perm_map = {"POST": ["catalog.change_product"]}

    def post(self, request, pk, action):
        product = get_object_or_404(Product, pk=pk)
        if action == "publish":
            if not product.precio_venta_pen:
                return Response({"detail": "Para publicar, primero define el precio de venta."}, status=status.HTTP_400_BAD_REQUEST)
            if not product.imagenes.exists():
                return Response({"detail": "Agrega al menos una foto antes de publicar."}, status=status.HTTP_400_BAD_REQUEST)
            product.estado = Product.Estado.PUBLICADO
            product.save(update_fields=["estado", "actualizado_en"])
            product.sync_agotado()
        elif action == "hide":
            product.estado = Product.Estado.BORRADOR
            product.save(update_fields=["estado", "actualizado_en"])
        else:
            return Response(status=status.HTTP_404_NOT_FOUND)
        audit(request, AuditLog.Accion.ACCION, product, accion=action)
        return Response(AdminProductSerializer(Product.objects.get(pk=pk), context={"request": request}).data)


class ProductImagesView(StaffView):
    parser_classes = [MultiPartParser, FormParser]
    perm_map = {"POST": ["catalog.add_productimage"], "DELETE": ["catalog.delete_productimage"]}

    def post(self, request, pk):
        product = get_object_or_404(Product, pk=pk)
        files = request.FILES.getlist("imagen")
        if not files:
            return Response({"detail": "Selecciona al menos una foto."}, status=status.HTTP_400_BAD_REQUEST)
        created = []
        base = product.imagenes.count()
        for i, f in enumerate(files):
            try:
                validate_image_file(f)
            except Exception as exc:  # noqa: BLE001 - ValidationError de Django
                return Response({"detail": "; ".join(getattr(exc, "messages", [str(exc)]))}, status=status.HTTP_400_BAD_REQUEST)
            created.append(ProductImage.objects.create(producto=product, imagen=f, alt=product.nombre, orden=base + i))
        audit(request, AuditLog.Accion.ACCION, product, accion="subir_fotos", cantidad=len(created))
        return Response(AdminImageSerializer(created, many=True).data, status=status.HTTP_201_CREATED)

    def delete(self, request, pk):
        image = get_object_or_404(ProductImage, pk=request.query_params.get("imagen"), producto_id=pk)
        audit(request, AuditLog.Accion.ELIMINAR, image)
        image.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class VariantCreateView(StaffView):
    perm_map = {"POST": ["catalog.add_productvariant"]}

    def post(self, request, pk):
        product = get_object_or_404(Product, pk=pk)
        nombre = (request.data.get("nombre") or "").strip()
        if not nombre:
            return Response({"nombre": "Indica el nombre de la variante."}, status=status.HTTP_400_BAD_REQUEST)
        atributo = request.data.get("atributo") or "color"
        if atributo not in ProductVariant.Atributo.values:
            return Response({"atributo": "Tipo no válido."}, status=status.HTTP_400_BAD_REQUEST)
        n = product.variantes.count() + 1
        sku = f"{product.slug.upper()[:30]}-{n}"
        while ProductVariant.objects.filter(sku=sku).exists():
            n += 1
            sku = f"{product.slug.upper()[:30]}-{n}"
        variant = ProductVariant.objects.create(producto=product, sku=sku, nombre=nombre, atributo=atributo)
        audit(request, AuditLog.Accion.CREAR, variant)
        return Response(AdminVariantSerializer(variant).data, status=status.HTTP_201_CREATED)


class VariantDetailView(StaffView):
    perm_map = {"PATCH": ["catalog.change_productvariant"]}

    def patch(self, request, pk):
        variant = get_object_or_404(ProductVariant, pk=pk)
        s = AdminVariantSerializer(variant, data=request.data, partial=True)
        s.is_valid(raise_exception=True)
        s.save()
        audit(request, AuditLog.Accion.EDITAR, variant, campos=sorted(s.validated_data.keys()))
        return Response(AdminVariantSerializer(variant).data)


class StockAdjustSerializer(serializers.Serializer):
    tipo = serializers.ChoiceField(choices=["entrada", "ajuste"])
    cantidad = serializers.IntegerField()
    motivo = serializers.CharField(min_length=3, max_length=200)

    def validate(self, attrs):
        if attrs["cantidad"] == 0:
            raise serializers.ValidationError({"cantidad": "La cantidad no puede ser cero."})
        if attrs["tipo"] == "entrada" and attrs["cantidad"] < 0:
            raise serializers.ValidationError({"cantidad": "Un ingreso debe ser mayor que cero."})
        return attrs


class VariantStockView(StaffView):
    perm_map = {"POST": ["catalog.change_productvariant"]}

    def post(self, request, pk):
        variant = get_object_or_404(ProductVariant, pk=pk)
        s = StockAdjustSerializer(data=request.data)
        s.is_valid(raise_exception=True)
        d = s.validated_data
        try:
            if d["tipo"] == "entrada":
                stock.add_stock(variant, d["cantidad"], d["motivo"], user=request.user)
            else:
                stock.adjust_stock(variant, d["cantidad"], d["motivo"], user=request.user)
        except stock.StockError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        audit(request, AuditLog.Accion.ACCION, variant, accion="ajustar_stock", **d)
        variant.refresh_from_db()
        return Response(AdminVariantSerializer(variant).data)


# --- Calculadora de precio y tipo de cambio ---------------------------------------

class PriceCalcSerializer(serializers.Serializer):
    precio_usd = serializers.DecimalField(max_digits=9, decimal_places=2, min_value=0)
    margen = serializers.DecimalField(max_digits=9, decimal_places=2, required=False)
    envio_usd = serializers.DecimalField(max_digits=8, decimal_places=2, required=False, min_value=0)
    impuestos_pct = serializers.DecimalField(max_digits=5, decimal_places=2, required=False, min_value=0)
    comision_pct = serializers.DecimalField(max_digits=5, decimal_places=2, required=False, min_value=0)
    tipo_cambio = serializers.DecimalField(max_digits=7, decimal_places=4, required=False, min_value=Decimal("0.0001"))


class PriceCalcView(StaffView):
    perm_map = {"POST": ["catalog.ver_finanzas"]}

    def post(self, request):
        s = PriceCalcSerializer(data=request.data)
        s.is_valid(raise_exception=True)
        d = s.validated_data
        cfg = StoreSettings.load()
        rate = d.get("tipo_cambio") or (ExchangeRate.current().usd_pen if ExchangeRate.current() else None)
        if rate is None:
            return Response({"detail": "Configura primero el tipo de cambio (Ajustes → Tipo de cambio)."}, status=status.HTTP_400_BAD_REQUEST)
        try:
            r = calculate_price(
                precio_usd=d["precio_usd"], tipo_cambio=rate,
                envio_usd=d.get("envio_usd", cfg.envio_estimado_usd), impuestos_pct=d.get("impuestos_pct", cfg.impuestos_estimados_pct),
                margen_pen=d.get("margen", cfg.margen_default), comision_pct=d.get("comision_pct", cfg.pct_comision),
                igv_rate=settings.IGV_RATE, multiplo=cfg.redondeo_multiplo,
            )
        except PricingError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        return Response({"tipo_cambio": str(rate), **{k: str(v) for k, v in r.__dict__.items()}})


class ExchangeRateView(StaffView):
    perm_map = {"GET": ["core.view_exchangerate"], "POST": ["core.add_exchangerate"]}

    def get(self, request):
        return Response([{"id": r.pk, "usd_pen": str(r.usd_pen), "vigente_desde": r.vigente_desde.isoformat()} for r in ExchangeRate.objects.all()[:20]])

    def post(self, request):
        try:
            value = Decimal(str(request.data.get("usd_pen")))
        except Exception:  # noqa: BLE001
            return Response({"usd_pen": "Valor no válido."}, status=status.HTTP_400_BAD_REQUEST)
        if value <= 0 or value > 100:
            return Response({"usd_pen": "Valor no válido."}, status=status.HTTP_400_BAD_REQUEST)
        rate = ExchangeRate.objects.create(usd_pen=value, creado_por=request.user)
        audit(request, AuditLog.Accion.CREAR, rate)
        return Response({"id": rate.pk, "usd_pen": str(rate.usd_pen), "vigente_desde": rate.vigente_desde.isoformat()}, status=status.HTTP_201_CREATED)


class StoreSettingsSerializer(serializers.ModelSerializer):
    class Meta:
        model = StoreSettings
        exclude = ("id",)


class StoreSettingsView(StaffView):
    perm_map = {"GET": ["core.view_storesettings"], "PATCH": ["core.change_storesettings"]}

    def get(self, request):
        return Response(StoreSettingsSerializer(StoreSettings.load()).data)

    def patch(self, request):
        cfg = StoreSettings.load()
        s = StoreSettingsSerializer(cfg, data=request.data, partial=True)
        s.is_valid(raise_exception=True)
        s.save()
        audit(request, AuditLog.Accion.EDITAR, cfg, campos=sorted(s.validated_data.keys()))
        return Response(s.data)


# --- Pedidos y pagos -----------------------------------------------------------------

def order_payload(order, user):
    can_pay = user.has_perm("payments.view_payment")
    addr = order.direccion_entrega or {}
    data = {
        "id": order.pk, "token": str(order.public_token), "estado": order.estado, "tipo_venta": order.tipo_venta,
        "creado_en": order.creado_en, "total_pen": str(order.total_pen), "envio_pen": str(order.envio_pen), "subtotal_pen": str(order.subtotal_pen), "descuento_pen": str(order.descuento_pen),
        "adelanto_pen": str(order.adelanto_pen), "saldo_pen": str(order.saldo_pendiente), "metodo_entrega": order.metodo_entrega,
        "cliente": {"nombre": order.cliente.nombre, "telefono": order.cliente.telefono, "email": order.cliente.email},
        "direccion": addr, "notas": order.notas,
        "items": [{"nombre": i.nombre_snapshot, "sku": i.sku_snapshot, "precio": str(i.precio_unitario), "cantidad": i.cantidad} for i in order.items.all()],
        "historial": [{"estado": h.estado_nuevo, "nota": h.nota, "fecha": h.creado_en, "usuario": h.usuario.get_username() if h.usuario else None} for h in order.historial.all()],
        "siguientes": sorted(x.value for x in order_services.ALLOWED_TRANSITIONS.get(order.estado, set())),
    }
    if can_pay:
        data["pagos"] = [
            {"id": p.pk, "proveedor": p.proveedor, "metodo": p.metodo, "monto": str(p.monto), "estado": p.estado, "es_adelanto": p.es_adelanto,
             "nota": p.nota, "comprobante": p.comprobante.url if p.comprobante else None, "creado_en": p.creado_en}
            for p in order.pagos.all()
        ]
    return data


class OrderListView(StaffView):
    perm_map = {"GET": ["orders.view_order"]}

    def get(self, request):
        qs = Order.objects.select_related("cliente").order_by("-creado_en")
        estado, q = request.query_params.get("estado"), request.query_params.get("q")
        if estado:
            qs = qs.filter(estado=estado)
        if q:
            cond = Q(cliente__nombre__icontains=q) | Q(cliente__telefono__icontains=q)
            if q.isdigit():
                cond |= Q(pk=int(q))
            qs = qs.filter(cond)
        rows = [
            {"id": o.pk, "estado": o.estado, "tipo_venta": o.tipo_venta, "total_pen": str(o.total_pen), "cliente": o.cliente.nombre,
             "telefono": o.cliente.telefono, "creado_en": o.creado_en, "items": o.items.count()}
            for o in qs[:200]
        ]
        return Response(rows)


class OrderDetailView(StaffView):
    perm_map = {"GET": ["orders.view_order"]}

    def get(self, request, pk):
        order = get_object_or_404(Order.objects.select_related("cliente").prefetch_related("items", "historial__usuario", "pagos"), pk=pk)
        return Response(order_payload(order, request.user))


class OrderTransitionView(StaffView):
    perm_map = {"POST": ["orders.change_order"]}

    def post(self, request, pk):
        order = get_object_or_404(Order, pk=pk)
        estado = request.data.get("estado")
        if estado not in Order.Estado.values:
            return Response({"estado": "Estado no válido."}, status=status.HTTP_400_BAD_REQUEST)
        try:
            order_services.transition(order, estado, user=request.user, nota=str(request.data.get("nota") or "Desde el panel")[:255])
        except order_services.OrderError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_409_CONFLICT)
        audit(request, AuditLog.Accion.ACCION, order, estado=estado)
        order = Order.objects.select_related("cliente").prefetch_related("items", "historial__usuario", "pagos").get(pk=pk)
        return Response(order_payload(order, request.user))


class PaymentActionView(StaffView):
    perm_map = {"POST": ["payments.change_payment"]}

    def post(self, request, pk, action):
        payment = get_object_or_404(Payment, pk=pk)
        try:
            if action == "approve":
                payment_services.approve_payment(payment, user=request.user)
            elif action == "reject":
                payment_services.reject_payment(payment, user=request.user, nota=str(request.data.get("nota") or "Rechazado desde el panel"))
            else:
                return Response(status=status.HTTP_404_NOT_FOUND)
        except payment_services.PaymentError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_409_CONFLICT)
        audit(request, AuditLog.Accion.ACCION, payment, accion=action)
        order = Order.objects.select_related("cliente").prefetch_related("items", "historial__usuario", "pagos").get(pk=payment.pedido_id)
        return Response(order_payload(order, request.user))


class AuditLogView(StaffView):
    perm_map = {"GET": ["core.view_auditlog"]}

    def get(self, request):
        rows = AuditLog.objects.select_related("usuario")[:100]
        return Response([
            {"id": a.pk, "fecha": a.creado_en, "usuario": a.usuario.get_username() if a.usuario else None, "accion": a.accion, "modelo": a.modelo, "objeto": a.objeto_repr, "cambios": a.cambios}
            for a in rows
        ])
