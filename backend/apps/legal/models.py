from django.db import models


class Complaint(models.Model):
    """Hoja de reclamación del Libro de Reclamaciones virtual.

    Los campos siguen la hoja de reclamación de Indecopi; antes de salir a producción
    hay que verificar los requisitos vigentes para venta online.
    """

    class Tipo(models.TextChoices):
        RECLAMO = "reclamo", "Reclamo (disconformidad con el producto o servicio)"
        QUEJA = "queja", "Queja (malestar no relacionado al producto)"

    class Estado(models.TextChoices):
        RECIBIDO = "recibido", "Recibido"
        ATENDIDO = "atendido", "Atendido"

    correlativo = models.CharField(max_length=20, unique=True, editable=False)
    creado_en = models.DateTimeField(auto_now_add=True)

    # Consumidor
    nombre = models.CharField(max_length=160)
    doc_tipo = models.CharField(max_length=10, choices=[("DNI", "DNI"), ("CE", "CE"), ("PAS", "Pasaporte"), ("RUC", "RUC")])
    doc_numero = models.CharField(max_length=15)
    domicilio = models.CharField(max_length=255)
    telefono = models.CharField(max_length=20)
    email = models.EmailField()
    es_menor = models.BooleanField(default=False)
    apoderado = models.CharField("padre/madre/apoderado", max_length=160, blank=True)

    # Bien contratado
    bien = models.CharField(max_length=20, choices=[("producto", "Producto"), ("servicio", "Servicio")], default="producto")
    monto_reclamado = models.DecimalField(max_digits=9, decimal_places=2, null=True, blank=True)
    descripcion_bien = models.CharField(max_length=255)
    pedido_ref = models.CharField("número de pedido", max_length=40, blank=True)

    # Reclamo
    tipo = models.CharField(max_length=10, choices=Tipo.choices)
    detalle = models.TextField()
    pedido_consumidor = models.TextField("pedido del consumidor")

    # Atención
    estado = models.CharField(max_length=10, choices=Estado.choices, default=Estado.RECIBIDO, db_index=True)
    respuesta = models.TextField(blank=True)
    respondido_en = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-creado_en"]
        verbose_name = "reclamación"
        verbose_name_plural = "reclamaciones"

    def __str__(self):
        return self.correlativo

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        if not self.correlativo:
            self.correlativo = f"{self.creado_en:%Y}-{self.pk:06d}"
            super().save(update_fields=["correlativo"])
