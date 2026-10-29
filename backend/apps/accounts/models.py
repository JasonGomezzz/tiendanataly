from django.conf import settings
from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    """Usuario del sistema. El username es el email en clientas registradas."""

    email = models.EmailField("correo", unique=True)
    telefono = models.CharField(max_length=20, blank=True)

    @property
    def is_staff_role(self):
        return self.is_staff and self.groups.filter(name__in=["Administradora", "Staff"]).exists()


class Customer(models.Model):
    """Datos de contacto de quien compra; la cuenta (user) es opcional (compra como invitada)."""

    user = models.OneToOneField(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="customer")
    nombre = models.CharField(max_length=120)
    telefono = models.CharField(max_length=20)
    email = models.EmailField(blank=True)
    # Reservado para boleta/factura (sin implementar): DNI o RUC.
    doc_tipo = models.CharField(max_length=3, blank=True, choices=[("DNI", "DNI"), ("RUC", "RUC")])
    doc_numero = models.CharField(max_length=15, blank=True)
    anonimizado = models.BooleanField(default=False)
    creado_en = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "clienta"
        verbose_name_plural = "clientas"

    def __str__(self):
        return self.nombre

    def anonymize(self):
        """Derecho a eliminar datos (Ley 29733): borra datos personales, conserva pedidos."""
        self.nombre = "Cliente eliminada"
        self.telefono = ""
        self.email = ""
        self.doc_tipo = ""
        self.doc_numero = ""
        self.anonimizado = True
        self.save()
        self.addresses.all().delete()
        if self.user_id:
            user = self.user
            user.is_active = False
            user.email = f"eliminado-{user.pk}@invalid.local"
            user.username = f"eliminado-{user.pk}"
            user.first_name = user.last_name = user.telefono = ""
            user.set_unusable_password()
            user.save()


class Address(models.Model):
    customer = models.ForeignKey(Customer, on_delete=models.CASCADE, related_name="addresses")
    etiqueta = models.CharField(max_length=40, blank=True, help_text="Casa, trabajo…")
    destinatario = models.CharField(max_length=120)
    telefono = models.CharField(max_length=20)
    departamento = models.CharField(max_length=60, default="Lima")
    provincia = models.CharField(max_length=60, default="Lima")
    distrito = models.CharField(max_length=60)
    direccion = models.CharField(max_length=255)
    referencia = models.CharField(max_length=255, blank=True)
    principal = models.BooleanField(default=False)

    class Meta:
        verbose_name = "dirección"
        verbose_name_plural = "direcciones"

    def __str__(self):
        return f"{self.direccion}, {self.distrito}"

    @property
    def es_lima_metropolitana(self):
        return self.departamento.strip().lower() == "lima" and self.provincia.strip().lower() == "lima"


class Consent(models.Model):
    """Consentimiento explícito (Ley 29733): política de privacidad y términos."""

    class Tipo(models.TextChoices):
        PRIVACIDAD = "privacidad", "Política de privacidad"
        TERMINOS = "terminos", "Términos y condiciones"
        MARKETING = "marketing", "Comunicaciones comerciales"

    customer = models.ForeignKey(Customer, on_delete=models.CASCADE, related_name="consents")
    tipo = models.CharField(max_length=12, choices=Tipo.choices)
    version = models.CharField(max_length=20, default="1")
    aceptado_en = models.DateTimeField(auto_now_add=True)
    ip = models.GenericIPAddressField(null=True, blank=True)

    class Meta:
        verbose_name = "consentimiento"
        verbose_name_plural = "consentimientos"
