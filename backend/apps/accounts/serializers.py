from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from rest_framework import serializers

from .models import Address, Customer

User = get_user_model()


class RegisterSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True, trim_whitespace=False)
    nombre = serializers.CharField(max_length=120)
    telefono = serializers.CharField(max_length=20)
    acepta_privacidad = serializers.BooleanField()
    acepta_terminos = serializers.BooleanField()
    acepta_marketing = serializers.BooleanField(required=False, default=False)

    def validate_email(self, value):
        value = value.strip().lower()
        if User.objects.filter(email__iexact=value).exists():
            # Mensaje genérico: no revela qué correos tienen cuenta.
            raise serializers.ValidationError("No se pudo registrar con ese correo.")
        return value

    def validate_acepta_privacidad(self, value):
        if not value:
            raise serializers.ValidationError("Debes aceptar la política de privacidad.")
        return value

    def validate_acepta_terminos(self, value):
        if not value:
            raise serializers.ValidationError("Debes aceptar los términos y condiciones.")
        return value

    def validate(self, attrs):
        candidate = User(username=attrs["email"], email=attrs["email"], first_name=attrs["nombre"])
        validate_password(attrs["password"], candidate)
        return attrs


class LoginSerializer(serializers.Serializer):
    email = serializers.CharField()
    password = serializers.CharField(trim_whitespace=False)
    otp_token = serializers.CharField(required=False, allow_blank=True)


class CustomerSerializer(serializers.ModelSerializer):
    email = serializers.EmailField(source="user.email", read_only=True)

    class Meta:
        model = Customer
        fields = ("id", "nombre", "telefono", "email", "doc_tipo", "doc_numero")


class AddressSerializer(serializers.ModelSerializer):
    class Meta:
        model = Address
        fields = ("id", "etiqueta", "destinatario", "telefono", "departamento", "provincia", "distrito", "direccion", "referencia", "principal")


class PasswordResetRequestSerializer(serializers.Serializer):
    email = serializers.EmailField()


class PasswordResetConfirmSerializer(serializers.Serializer):
    uid = serializers.CharField()
    token = serializers.CharField()
    password = serializers.CharField(trim_whitespace=False)
