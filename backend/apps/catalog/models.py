from decimal import Decimal

from django.conf import settings
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.db.models import F, Q

from apps.core.validators import uuid_upload_path, validate_image_file


class Category(models.Model):
    nombre = models.CharField(max_length=80)
    slug = models.SlugField(unique=True)
    orden = models.PositiveSmallIntegerField(default=0)

    class Meta:
        ordering = ["orden", "nombre"]
        verbose_name = "categoría"
        verbose_name_plural = "categorías"

    def __str__(self):
        return self.nombre


class Brand(models.Model):
    nombre = models.CharField(max_length=80)
    slug = models.SlugField(unique=True)

    class Meta:
        ordering = ["nombre"]
        verbose_name = "marca"

    def __str__(self):
        return self.nombre


class Product(models.Model):
    class Estado(models.TextChoices):
        BORRADOR = "borrador", "Borrador"
        PUBLICADO = "publicado", "Publicado"
        AGOTADO = "agotado", "Agotado"

    class TipoVenta(models.TextChoices):
        STOCK_LOCAL = "stock_local", "Stock en Lima"
        POR_ENCARGO = "por_encargo", "Por encargo"

    nombre = models.CharField(max_length=160)
    slug = models.SlugField(max_length=160, unique=True)
    descripcion = models.TextField(blank=True)
    detalles = models.TextField("detalles del producto", blank=True)
    marca = models.ForeignKey(Brand, on_delete=models.PROTECT, related_name="productos")
    categoria = models.ForeignKey(Category, on_delete=models.PROTECT, related_name="productos")
    linea = models.CharField("línea / presentación", max_length=120, blank=True)
    estado = models.CharField(max_length=10, choices=Estado.choices, default=Estado.BORRADOR, db_index=True)
    tipo_venta = models.CharField(max_length=12, choices=TipoVenta.choices, default=TipoVenta.STOCK_LOCAL)
    orden = models.PositiveIntegerField("orden de aparición", default=0)

    # Finanzas: visibles solo con el permiso catalog.ver_finanzas
    precio_compra_usd = models.DecimalField("precio de compra (US$)", max_digits=9, decimal_places=2, null=True, blank=True, validators=[MinValueValidator(Decimal("0"))])
    margen = models.DecimalField("margen (S/)", max_digits=9, decimal_places=2, null=True, blank=True)
    precio_venta_pen = models.DecimalField("precio de venta (S/)", max_digits=9, decimal_places=2, null=True, blank=True, validators=[MinValueValidator(Decimal("0"))])

    notas_internas = models.TextField(blank=True, help_text="Solo visible en el admin.")
    creado_en = models.DateTimeField(auto_now_add=True)
    actualizado_en = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["orden", "nombre"]
        verbose_name = "producto"
        permissions = [("ver_finanzas", "Puede ver costos, márgenes y finanzas")]
        indexes = [models.Index(fields=["estado", "orden"])]

    def __str__(self):
        return self.nombre

    @property
    def sin_imagen(self):
        return not self.imagenes.exists()

    @property
    def stock_total_disponible(self):
        return sum(v.disponible for v in self.variantes.all() if v.activo)

    @property
    def visible(self):
        return self.estado in (self.Estado.PUBLICADO, self.Estado.AGOTADO)

    def sync_agotado(self):
        """Alterna publicado <-> agotado según el stock disponible real."""
        if self.tipo_venta == self.TipoVenta.POR_ENCARGO:
            return  # los pedidos por encargo no dependen del stock en Lima
        total = self.stock_total_disponible
        if self.estado == self.Estado.PUBLICADO and total <= 0:
            self.estado = self.Estado.AGOTADO
            self.save(update_fields=["estado", "actualizado_en"])
        elif self.estado == self.Estado.AGOTADO and total > 0:
            self.estado = self.Estado.PUBLICADO
            self.save(update_fields=["estado", "actualizado_en"])


class ProductVariant(models.Model):
    class Atributo(models.TextChoices):
        UNICO = "unico", "Única"
        COLOR = "color", "Color"
        FRAGANCIA = "fragancia", "Fragancia"
        TALLA = "talla", "Talla"

    producto = models.ForeignKey(Product, on_delete=models.CASCADE, related_name="variantes")
    sku = models.CharField(max_length=40, unique=True)
    nombre = models.CharField("variante", max_length=80, default="Única")
    atributo = models.CharField(max_length=10, choices=Atributo.choices, default=Atributo.UNICO)
    # El stock solo cambia por el servicio de inventario (deja un InventoryMovement).
    stock_disponible = models.PositiveIntegerField("stock físico", default=0)
    stock_reservado = models.PositiveIntegerField("stock reservado", default=0)
    activo = models.BooleanField(default=True)

    class Meta:
        ordering = ["producto", "id"]
        verbose_name = "variante"
        constraints = [
            models.CheckConstraint(condition=Q(stock_reservado__lte=F("stock_disponible")), name="reservado_no_supera_disponible"),
        ]

    def __str__(self):
        return f"{self.producto.nombre} — {self.nombre}"

    @property
    def disponible(self):
        """Unidades que se pueden vender ahora (físico menos reservado)."""
        return self.stock_disponible - self.stock_reservado


class ProductImage(models.Model):
    producto = models.ForeignKey(Product, on_delete=models.CASCADE, related_name="imagenes")
    imagen = models.ImageField(upload_to=uuid_upload_path("productos"), validators=[validate_image_file])
    alt = models.CharField("texto alternativo", max_length=200, blank=True)
    orden = models.PositiveSmallIntegerField(default=0)

    class Meta:
        ordering = ["orden", "id"]
        verbose_name = "imagen"
        verbose_name_plural = "imágenes"

    def __str__(self):
        return f"{self.producto.nombre} #{self.orden}"


class Collection(models.Model):
    nombre = models.CharField(max_length=100)
    slug = models.SlugField(unique=True)
    descripcion = models.TextField(blank=True)
    activa = models.BooleanField(default=True)
    orden = models.PositiveSmallIntegerField(default=0)
    productos = models.ManyToManyField(Product, blank=True, related_name="colecciones")

    class Meta:
        ordering = ["orden", "nombre"]
        verbose_name = "colección"
        verbose_name_plural = "colecciones"

    def __str__(self):
        return self.nombre


class StockAlert(models.Model):
    """'Avísame cuando vuelva' para una variante agotada."""

    variante = models.ForeignKey(ProductVariant, on_delete=models.CASCADE, related_name="alertas")
    email = models.EmailField(blank=True)
    telefono = models.CharField(max_length=20, blank=True)
    notificado = models.BooleanField(default=False)
    creado_en = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "alerta de stock"
        verbose_name_plural = "alertas de stock"


class Review(models.Model):
    class Estado(models.TextChoices):
        PENDIENTE = "pendiente", "Pendiente"
        APROBADA = "aprobada", "Aprobada"
        RECHAZADA = "rechazada", "Rechazada"

    producto = models.ForeignKey(Product, on_delete=models.CASCADE, related_name="resenas")
    cliente = models.ForeignKey("accounts.Customer", null=True, blank=True, on_delete=models.SET_NULL, related_name="resenas")
    autor = models.CharField(max_length=80)
    puntaje = models.PositiveSmallIntegerField(validators=[MinValueValidator(1), MaxValueValidator(5)])
    comentario = models.TextField(max_length=1000)
    foto = models.ImageField(upload_to=uuid_upload_path("resenas"), validators=[validate_image_file], blank=True)
    estado = models.CharField(max_length=10, choices=Estado.choices, default=Estado.PENDIENTE, db_index=True)
    creado_en = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-creado_en"]
        verbose_name = "reseña"
