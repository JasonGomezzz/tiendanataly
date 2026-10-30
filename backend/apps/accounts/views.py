from django.conf import settings
from django.contrib.auth import authenticate, get_user_model, login, logout
from django.contrib.auth.tokens import default_token_generator
from django.core.exceptions import ValidationError as DjangoValidationError
from django.contrib.auth.password_validation import validate_password
from django.core.mail import send_mail
from django.db import transaction
from django.middleware.csrf import get_token
from django.utils.decorators import method_decorator
from django.utils.encoding import force_bytes, force_str
from django.utils.http import urlsafe_base64_decode, urlsafe_base64_encode
from django.views.decorators.csrf import ensure_csrf_cookie
from axes.handlers.proxy import AxesProxyHandler
from django_otp import devices_for_user, login as otp_login
from rest_framework import status, viewsets
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.core.api import CsrfProtectedMixin, ScopedThrottleMixin
from apps.core.ip import client_ip

from .models import Consent, Customer
from .serializers import (
    AddressSerializer,
    CustomerSerializer,
    LoginSerializer,
    PasswordResetConfirmSerializer,
    PasswordResetRequestSerializer,
    RegisterSerializer,
)

User = get_user_model()


def _client_ip(request):
    return client_ip(request)


@method_decorator(ensure_csrf_cookie, name="dispatch")
class CsrfView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []

    def get(self, request):
        return Response({"csrfToken": get_token(request)})


class RegisterView(CsrfProtectedMixin, ScopedThrottleMixin, APIView):
    permission_classes = [AllowAny]
    throttle_scope = "register"

    @transaction.atomic
    def post(self, request):
        s = RegisterSerializer(data=request.data)
        s.is_valid(raise_exception=True)
        d = s.validated_data
        user = User.objects.create_user(username=d["email"], email=d["email"], password=d["password"], first_name=d["nombre"], telefono=d["telefono"])
        customer = Customer.objects.create(user=user, nombre=d["nombre"], telefono=d["telefono"], email=d["email"])
        ip = _client_ip(request)
        Consent.objects.create(customer=customer, tipo=Consent.Tipo.PRIVACIDAD, ip=ip)
        Consent.objects.create(customer=customer, tipo=Consent.Tipo.TERMINOS, ip=ip)
        if d["acepta_marketing"]:
            Consent.objects.create(customer=customer, tipo=Consent.Tipo.MARKETING, ip=ip)
        login(request, user, backend="django.contrib.auth.backends.ModelBackend")
        return Response(CustomerSerializer(customer).data, status=status.HTTP_201_CREATED)


class LoginView(CsrfProtectedMixin, ScopedThrottleMixin, APIView):
    permission_classes = [AllowAny]
    throttle_scope = "login"

    def post(self, request):
        s = LoginSerializer(data=request.data)
        s.is_valid(raise_exception=True)
        d = s.validated_data
        username = d["email"].strip().lower()
        http_request = request._request  # django-axes trabaja con el HttpRequest, no con el Request de DRF
        if not AxesProxyHandler.is_allowed(http_request, {"username": username}):
            return Response({"detail": "Demasiados intentos. Inténtalo más tarde."}, status=status.HTTP_429_TOO_MANY_REQUESTS)
        user = authenticate(http_request, username=username, password=d["password"])
        if user is None or not user.is_active:
            return Response({"detail": "Credenciales inválidas."}, status=status.HTTP_400_BAD_REQUEST)

        device = None
        if user.is_staff:  # 2FA obligatorio para Admin y Staff también por la API
            devices = list(devices_for_user(user, confirmed=True))
            if not devices:
                return Response({"detail": "Tu cuenta requiere 2FA y aún no está configurado. Contacta al desarrollador."}, status=status.HTTP_403_FORBIDDEN)
            token = (d.get("otp_token") or "").strip()
            if not token:
                return Response({"detail": "Ingresa el código de tu app de autenticación.", "otp_required": True}, status=status.HTTP_401_UNAUTHORIZED)
            device = next((dev for dev in devices if dev.verify_token(token)), None)
            if device is None:
                return Response({"detail": "Código incorrecto.", "otp_required": True}, status=status.HTTP_400_BAD_REQUEST)

        login(request, user)
        if device is not None:
            otp_login(request, device)
        customer = getattr(user, "customer", None)
        return Response({"id": user.pk, "email": user.email, "nombre": customer.nombre if customer else user.get_username(), "is_staff": user.is_staff})


class LogoutView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        logout(request)
        return Response(status=status.HTTP_204_NO_CONTENT)


class MeView(APIView):
    permission_classes = [IsAuthenticated]

    def _customer(self, request):
        customer, _ = Customer.objects.get_or_create(
            user=request.user,
            defaults={"nombre": request.user.get_full_name() or request.user.get_username(), "telefono": request.user.telefono, "email": request.user.email},
        )
        return customer

    def get(self, request):
        return Response(CustomerSerializer(self._customer(request)).data)

    def patch(self, request):
        customer = self._customer(request)
        s = CustomerSerializer(customer, data=request.data, partial=True)
        s.is_valid(raise_exception=True)
        s.save()
        return Response(s.data)

    @transaction.atomic
    def delete(self, request):
        """Derecho a eliminar datos personales (Ley 29733): anonimiza y cierra la sesión."""
        self._customer(request).anonymize()
        logout(request)
        return Response(status=status.HTTP_204_NO_CONTENT)


class AddressViewSet(viewsets.ModelViewSet):
    serializer_class = AddressSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = []
    pagination_class = None

    def _customer(self):
        customer, _ = Customer.objects.get_or_create(
            user=self.request.user,
            defaults={"nombre": self.request.user.get_username(), "telefono": self.request.user.telefono, "email": self.request.user.email},
        )
        return customer

    def get_queryset(self):
        # Siempre filtrado por la dueña: otra clienta recibe 404 al pedir una dirección ajena.
        return self._customer().addresses.all()

    def perform_create(self, serializer):
        serializer.save(customer=self._customer())


class PasswordResetRequestView(CsrfProtectedMixin, ScopedThrottleMixin, APIView):
    permission_classes = [AllowAny]
    throttle_scope = "password_reset"

    def post(self, request):
        s = PasswordResetRequestSerializer(data=request.data)
        s.is_valid(raise_exception=True)
        user = User.objects.filter(email__iexact=s.validated_data["email"], is_active=True, is_staff=False).first()
        if user:
            uid = urlsafe_base64_encode(force_bytes(user.pk))
            token = default_token_generator.make_token(user)
            send_mail(
                f"Restablece tu contraseña de {settings.STORE_NAME}",
                "Hola,\n\nUsa este enlace para elegir una nueva contraseña (vence en unas horas):\n"
                f"{settings.SITE_URL}/restablecer?uid={uid}&token={token}\n\n"
                "Si no lo pediste tú, ignora este mensaje.",
                None,
                [user.email],
            )
        # Misma respuesta exista o no la cuenta (no revela qué correos están registrados).
        return Response({"detail": "Si el correo existe, te enviamos instrucciones."})


class PasswordResetConfirmView(CsrfProtectedMixin, ScopedThrottleMixin, APIView):
    permission_classes = [AllowAny]
    throttle_scope = "password_reset"

    def post(self, request):
        s = PasswordResetConfirmSerializer(data=request.data)
        s.is_valid(raise_exception=True)
        d = s.validated_data
        try:
            user = User.objects.get(pk=force_str(urlsafe_base64_decode(d["uid"])), is_staff=False)
        except (User.DoesNotExist, ValueError, TypeError, OverflowError):
            user = None
        if user is None or not default_token_generator.check_token(user, d["token"]):
            return Response({"detail": "El enlace no es válido o venció."}, status=status.HTTP_400_BAD_REQUEST)
        try:
            validate_password(d["password"], user)
        except DjangoValidationError as exc:
            return Response({"password": list(exc.messages)}, status=status.HTTP_400_BAD_REQUEST)
        user.set_password(d["password"])
        user.save()
        return Response({"detail": "Contraseña actualizada."})
