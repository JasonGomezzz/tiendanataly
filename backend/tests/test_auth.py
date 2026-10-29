import pytest
from django.contrib.auth import get_user_model
from django_otp.oath import TOTP
from django_otp.plugins.otp_totp.models import TOTPDevice
from rest_framework.test import APIClient
from rest_framework.throttling import ScopedRateThrottle

from apps.accounts.models import Consent, Customer
from tests.factories import PASSWORD, make_user

pytestmark = pytest.mark.django_db
User = get_user_model()

REGISTER = {
    "email": "Nueva@Example.com", "password": PASSWORD, "nombre": "Nueva Clienta", "telefono": "987654321",
    "acepta_privacidad": True, "acepta_terminos": True,
}


def totp_token(device):
    return str(TOTP(device.bin_key, device.step, device.t0, device.digits, device.drift).token()).zfill(device.digits)


# --- Registro y consentimiento (Ley 29733) ----------------------------------

def test_registro_crea_cuenta_clienta_y_consentimientos(api):
    r = api.post("/api/v1/auth/register/", REGISTER, format="json")
    assert r.status_code == 201
    user = User.objects.get(email="nueva@example.com")
    assert not user.is_staff and not user.is_superuser
    assert set(Consent.objects.filter(customer__user=user).values_list("tipo", flat=True)) == {"privacidad", "terminos"}
    assert api.get("/api/v1/me/").status_code == 200  # quedó con sesión


@pytest.mark.parametrize("missing", ["acepta_privacidad", "acepta_terminos"])
def test_registro_exige_consentimiento_explicito(api, missing):
    r = api.post("/api/v1/auth/register/", {**REGISTER, missing: False}, format="json")
    assert r.status_code == 400
    assert not User.objects.filter(email="nueva@example.com").exists()


def test_registro_rechaza_contrasenas_debiles(api):
    for weak in ("corta1", "1234567890", "password123"):
        assert api.post("/api/v1/auth/register/", {**REGISTER, "password": weak}, format="json").status_code == 400


def test_registro_no_permite_correo_repetido(api):
    api.post("/api/v1/auth/register/", REGISTER, format="json")
    assert APIClient().post("/api/v1/auth/register/", REGISTER, format="json").status_code == 400


# --- Login ------------------------------------------------------------------

def test_login_correcto_y_logout(api, customer_user):
    r = api.post("/api/v1/auth/login/", {"email": "CLIENTA1@example.com", "password": PASSWORD}, format="json")
    assert r.status_code == 200
    assert api.get("/api/v1/me/").status_code == 200
    assert api.post("/api/v1/auth/logout/").status_code == 204
    assert api.get("/api/v1/me/").status_code in (401, 403)


def test_login_incorrecto_da_mensaje_generico(api, customer_user):
    wrong_pass = api.post("/api/v1/auth/login/", {"email": "clienta1@example.com", "password": "mala-clave-1"}, format="json")
    no_user = api.post("/api/v1/auth/login/", {"email": "nadie@example.com", "password": "mala-clave-1"}, format="json")
    assert wrong_pass.status_code == no_user.status_code == 400
    assert wrong_pass.json() == no_user.json()


def test_bloqueo_temporal_tras_intentos_fallidos(api, customer_user):
    for _ in range(5):
        api.post("/api/v1/auth/login/", {"email": "clienta1@example.com", "password": "mala-clave-1"}, format="json")
    # Aun con la contraseña correcta, queda bloqueada temporalmente.
    r = api.post("/api/v1/auth/login/", {"email": "clienta1@example.com", "password": PASSWORD}, format="json")
    assert r.status_code == 429


def test_login_exige_csrf(customer_user):
    strict = APIClient(enforce_csrf_checks=True)
    r = strict.post("/api/v1/auth/login/", {"email": "clienta1@example.com", "password": PASSWORD}, format="json")
    assert r.status_code == 403
    token = strict.get("/api/v1/auth/csrf/").json()["csrfToken"]
    r = strict.post("/api/v1/auth/login/", {"email": "clienta1@example.com", "password": PASSWORD}, format="json", HTTP_X_CSRFTOKEN=token)
    assert r.status_code == 200


def test_la_cookie_de_sesion_es_httponly(api, customer_user):
    r = api.post("/api/v1/auth/login/", {"email": "clienta1@example.com", "password": PASSWORD}, format="json")
    assert r.cookies["sessionid"]["httponly"] is True
    assert r.cookies["sessionid"]["samesite"] == "Lax"


def test_la_api_no_entrega_tokens_en_el_cuerpo(api, customer_user):
    body = api.post("/api/v1/auth/login/", {"email": "clienta1@example.com", "password": PASSWORD}, format="json").json()
    assert not any("token" in k.lower() for k in body)


# --- 2FA para Admin y Staff en la API ---------------------------------------

def test_staff_sin_2fa_configurado_no_puede_entrar_por_la_api(api, staff_role):
    r = api.post("/api/v1/auth/login/", {"email": "empleada@example.com", "password": PASSWORD}, format="json")
    assert r.status_code == 403
    assert api.get("/api/v1/me/").status_code in (401, 403)


def test_staff_debe_enviar_codigo_totp(api, admin_role):
    device = TOTPDevice.objects.create(user=admin_role, name="tel", confirmed=True)
    creds = {"email": "tia@example.com", "password": PASSWORD}
    r = api.post("/api/v1/auth/login/", creds, format="json")
    assert r.status_code == 401 and r.json()["otp_required"] is True
    assert api.post("/api/v1/auth/login/", {**creds, "otp_token": "000000"}, format="json").status_code == 400
    r = api.post("/api/v1/auth/login/", {**creds, "otp_token": totp_token(device)}, format="json")
    assert r.status_code == 200 and r.json()["is_staff"] is True


# --- Cuenta y derecho a eliminar -------------------------------------------

def test_eliminar_cuenta_anonimiza_los_datos_personales(api, customer_user):
    api.force_authenticate(customer_user)
    assert api.delete("/api/v1/me/").status_code == 204
    customer = Customer.objects.get(pk=customer_user.customer.pk)
    customer_user.refresh_from_db()
    assert customer.anonimizado and customer.nombre == "Cliente eliminada" and customer.telefono == ""
    assert not customer_user.is_active and "clienta1" not in customer_user.email


def test_recuperar_contrasena_no_revela_si_el_correo_existe(api, customer_user):
    a = api.post("/api/v1/auth/password/reset/", {"email": "clienta1@example.com"}, format="json")
    b = api.post("/api/v1/auth/password/reset/", {"email": "nadie@example.com"}, format="json")
    assert a.status_code == b.status_code == 200 and a.json() == b.json()


def test_flujo_de_recuperacion_de_contrasena(api, customer_user, mailoutbox):
    api.post("/api/v1/auth/password/reset/", {"email": "clienta1@example.com"}, format="json")
    body = mailoutbox[0].body
    assert body.count("http://localhost:3000/restablecer?uid=") == 1
    uid = body.split("uid=")[1].split("&")[0]
    token = body.split("token=")[1].split()[0]
    assert api.post("/api/v1/auth/password/reset/confirm/", {"uid": uid, "token": token, "password": "123"}, format="json").status_code == 400
    r = api.post("/api/v1/auth/password/reset/confirm/", {"uid": uid, "token": token, "password": "Otra-Clave-Segura-99"}, format="json")
    assert r.status_code == 200
    assert api.post("/api/v1/auth/login/", {"email": "clienta1@example.com", "password": "Otra-Clave-Segura-99"}, format="json").status_code == 200


# --- Rate limiting -----------------------------------------------------------

def test_limite_de_peticiones_en_login(api, monkeypatch):
    monkeypatch.setattr(ScopedRateThrottle, "THROTTLE_RATES", {"login": "3/min", "anon": "1000/min", "user": "1000/min"})
    codes = [api.post("/api/v1/auth/login/", {"email": f"x{i}@example.com", "password": "mala-clave-1"}, format="json").status_code for i in range(5)]
    assert 429 in codes


def test_limite_de_reclamaciones(api, monkeypatch):
    monkeypatch.setattr(ScopedRateThrottle, "THROTTLE_RATES", {"complaint": "2/hour", "anon": "1000/min", "user": "1000/min"})
    codes = [api.post("/api/v1/complaints/", {}, format="json").status_code for _ in range(4)]
    assert codes[-1] == 429


def test_headers_de_seguridad(api):
    r = api.get("/health/")
    assert r["X-Content-Type-Options"] == "nosniff"
    assert r["X-Frame-Options"] == "DENY"
    assert "camera=()" in r["Permissions-Policy"]
    assert r["Referrer-Policy"]
    assert "default-src" in r["Content-Security-Policy"]
