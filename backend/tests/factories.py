from datetime import timedelta
from decimal import Decimal
from itertools import count

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.utils import timezone

from apps.accounts.models import Customer
from apps.catalog.models import Brand, Category, Product, ProductVariant
from apps.inventory import services as stock
from apps.orders.models import Order, OrderItem

User = get_user_model()
_seq = count(1)
PASSWORD = "Contrasena-Segura-123"


def make_product(*, slug=None, stock_units=1, estado=Product.Estado.PUBLICADO, precio=Decimal("100"), variants=None):
    n = next(_seq)
    slug = slug or f"producto-{n}"
    brand, _ = Brand.objects.get_or_create(slug="vs", defaults={"nombre": "Victoria's Secret"})
    cat, _ = Category.objects.get_or_create(slug="bolsos", defaults={"nombre": "Bolsos"})
    product = Product.objects.create(
        nombre=slug.replace("-", " ").title(), slug=slug, marca=brand, categoria=cat, estado=estado,
        precio_compra_usd=Decimal("30"), margen=Decimal("40"), precio_venta_pen=precio,
    )
    specs = variants or [("Única", stock_units)]
    out = []
    for i, (nombre, units) in enumerate(specs):
        v = ProductVariant.objects.create(producto=product, sku=f"{slug}-{i}".upper()[:40], nombre=nombre)
        if units:
            stock.add_stock(v, units, "Stock inicial de prueba")
        out.append(v)
    product.refresh_from_db()
    return product, out


def make_user(username, *, groups=(), staff=False, superuser=False, password=PASSWORD):
    user = User.objects.create_user(username=f"{username}@example.com", email=f"{username}@example.com", password=password, is_staff=staff, is_superuser=superuser)
    for g in groups:
        user.groups.add(Group.objects.get(name=g))
    return user


def make_customer(user=None, nombre="Clienta Prueba"):
    return Customer.objects.create(user=user, nombre=nombre, telefono="999999999", email=user.email if user else "")


def make_order(variant, qty=1, *, customer=None, reserve=True, precio=Decimal("100"), minutes=15):
    customer = customer or make_customer()
    order = Order.objects.create(
        cliente=customer, subtotal_pen=precio * qty, total_pen=precio * qty,
        expira_en=timezone.now() + timedelta(minutes=minutes),
    )
    OrderItem.objects.create(pedido=order, variante=variant, nombre_snapshot=str(variant), sku_snapshot=variant.sku, precio_unitario=precio, cantidad=qty)
    if reserve:
        stock.reserve(variant, qty, order=order, minutes=minutes)
    return order
