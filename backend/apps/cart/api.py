import uuid

from django.conf import settings
from django.db import transaction
from rest_framework import serializers, status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.catalog.models import Product, ProductVariant
from apps.core.api import CsrfProtectedMixin, ScopedThrottleMixin

from .models import Cart, CartItem

COOKIE = "cart_token"
COOKIE_AGE = 60 * 60 * 24 * 30
MAX_PER_LINE = 10
PREORDER = Product.TipoVenta.POR_ENCARGO  # no depende del stock físico
SELLABLE = (Product.Estado.PUBLICADO, Product.Estado.AGOTADO)


def _cookie_token(request):
    try:
        return uuid.UUID(request.COOKIES.get(COOKIE, ""))
    except ValueError:
        return None


def get_cart(request, create=False):
    """Carrito de la usuaria autenticada o, si es invitada, el de su cookie."""
    if request.user.is_authenticated:
        cart = Cart.objects.filter(user=request.user).first()
        if cart is None and create:
            cart = Cart.objects.create(user=request.user)
        return cart
    token = _cookie_token(request)
    cart = Cart.objects.filter(token=token, user__isnull=True).first() if token else None
    if cart is None and create:
        cart = Cart.objects.create()
    return cart


def with_cookie(request, response, cart):
    if cart is not None and not request.user.is_authenticated and _cookie_token(request) != cart.token:
        response.set_cookie(
            COOKIE, str(cart.token), max_age=COOKIE_AGE, httponly=True, samesite="Lax", secure=settings.SESSION_COOKIE_SECURE,
        )
    return response


def serialize_cart(cart, request=None):
    items = []
    subtotal = 0
    if cart is not None:
        qs = cart.items.select_related("variante__producto").prefetch_related("variante__producto__imagenes").order_by("id")
        for it in qs:
            v, p = it.variante, it.variante.producto
            price = p.precio_venta_pen or 0
            vendible = v.activo and p.estado in SELLABLE and bool(p.precio_venta_pen)
            available = (MAX_PER_LINE if p.tipo_venta == PREORDER else max(v.disponible, 0)) if vendible else 0
            ok = vendible and it.cantidad <= available
            first = p.imagenes.all()[0] if p.imagenes.all() else None
            line = price * it.cantidad
            if ok:
                subtotal += line
            items.append({
                "id": it.pk,
                "variante_id": v.pk,
                "producto_slug": p.slug,
                "nombre": p.nombre,
                "variante": v.nombre if v.atributo != "unico" else "",
                "sku": v.sku,
                "imagen": first.imagen.url if first else None,
                "precio_unitario": str(price),
                "cantidad": it.cantidad,
                "subtotal": str(line),
                "disponible": available,
                "ok": ok,
            })
    return {"items": items, "count": sum(i["cantidad"] for i in items), "subtotal": str(subtotal)}


class AddItemSerializer(serializers.Serializer):
    variante_id = serializers.IntegerField()
    cantidad = serializers.IntegerField(min_value=1, max_value=MAX_PER_LINE, default=1)


class QuantitySerializer(serializers.Serializer):
    cantidad = serializers.IntegerField(min_value=1, max_value=MAX_PER_LINE)


def _check_variant(variant_id, qty):
    v = ProductVariant.objects.select_related("producto").filter(pk=variant_id, activo=True, producto__estado__in=SELLABLE).first()
    if v is None or not v.producto.precio_venta_pen:
        raise serializers.ValidationError({"variante_id": "Este producto no está disponible."})
    if v.producto.tipo_venta != PREORDER and v.disponible < qty:
        raise serializers.ValidationError({"cantidad": f"Solo quedan {max(v.disponible, 0)} unidades."}, code="sin_stock")
    return v


class CartView(ScopedThrottleMixin, APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        cart = get_cart(request)
        return Response(serialize_cart(cart))


class CartItemsView(CsrfProtectedMixin, ScopedThrottleMixin, APIView):
    permission_classes = [AllowAny]

    @transaction.atomic
    def post(self, request):
        s = AddItemSerializer(data=request.data)
        s.is_valid(raise_exception=True)
        cart = get_cart(request, create=True)
        existing = CartItem.objects.filter(cart=cart, variante_id=s.validated_data["variante_id"]).first()
        total = s.validated_data["cantidad"] + (existing.cantidad if existing else 0)
        if total > MAX_PER_LINE:
            raise serializers.ValidationError({"cantidad": f"Máximo {MAX_PER_LINE} por producto."})
        variant = _check_variant(s.validated_data["variante_id"], total)
        CartItem.objects.update_or_create(cart=cart, variante=variant, defaults={"cantidad": total})
        return with_cookie(request, Response(serialize_cart(cart), status=status.HTTP_201_CREATED), cart)


class CartItemDetailView(CsrfProtectedMixin, ScopedThrottleMixin, APIView):
    permission_classes = [AllowAny]

    def _item(self, request, pk):
        cart = get_cart(request)
        item = CartItem.objects.filter(cart=cart, pk=pk).first() if cart else None  # solo ítems de SU carrito
        return cart, item

    def patch(self, request, pk):
        cart, item = self._item(request, pk)
        if item is None:
            return Response(status=status.HTTP_404_NOT_FOUND)
        s = QuantitySerializer(data=request.data)
        s.is_valid(raise_exception=True)
        _check_variant(item.variante_id, s.validated_data["cantidad"])
        item.cantidad = s.validated_data["cantidad"]
        item.save(update_fields=["cantidad"])
        return Response(serialize_cart(cart))

    def delete(self, request, pk):
        cart, item = self._item(request, pk)
        if item is None:
            return Response(status=status.HTTP_404_NOT_FOUND)
        item.delete()
        return Response(serialize_cart(cart))


class CartMergeView(CsrfProtectedMixin, APIView):
    """Tras iniciar sesión: pasa los ítems del carrito de invitada (cookie) al carrito de la cuenta."""

    permission_classes = [AllowAny]

    @transaction.atomic
    def post(self, request):
        if not request.user.is_authenticated:
            return Response(status=status.HTTP_401_UNAUTHORIZED)
        token = _cookie_token(request)
        guest = Cart.objects.filter(token=token, user__isnull=True).first() if token else None
        mine = get_cart(request, create=True)
        if guest:
            for item in guest.items.all():
                other = CartItem.objects.filter(cart=mine, variante=item.variante).first()
                if other:
                    other.cantidad = min(other.cantidad + item.cantidad, MAX_PER_LINE)
                    other.save(update_fields=["cantidad"])
                else:
                    item.cart = mine
                    item.save(update_fields=["cart"])
            guest.delete()
        response = Response(serialize_cart(mine))
        response.delete_cookie(COOKIE)
        return response
