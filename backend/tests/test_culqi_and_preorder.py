import base64
import json
from decimal import Decimal

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile

from apps.catalog.models import Product
from apps.core.models import StoreSettings
from apps.inventory import services as stock
from apps.orders import services as orders
from apps.orders.models import Order
from apps.payments import services as payments
from apps.payments.models import Payment, PaymentEvent
from apps.payments.providers.culqi import CulqiProvider, to_cents
from apps.payments.providers.culqi_client import CulqiClient, CulqiError
from tests.factories import make_order, make_product

pytestmark = pytest.mark.django_db
E = Order.Estado
SECRET = "secreto-webhook"


@pytest.fixture(autouse=True)
def culqi_settings(settings):
    settings.CULQI_SECRET_KEY = "sk_test_x"
    settings.CULQI_PUBLIC_KEY = "pk_test_x"
    settings.CULQI_WEBHOOK_SECRET = SECRET
    settings.PAYMENTS_PROVIDER = "culqi"


def ok_charge(cents, **extra):
    return {
        "id": "chr_test_1", "object": "charge", "amount": cents, "currency_code": "PEN",
        "outcome": {"type": "venta_exitosa", "code": "AUT0000", "user_message": "ok"},
        "source": {"card_number": "411111******1111", "iin": {"card_brand": "Visa"}},  # nunca debe guardarse
        "metadata": {"pedido": "1"}, **extra,
    }


def charge_url(order):
    return f"/api/v1/orders/{order.public_token}/payments/culqi/charge/"


def webhook(api, event, secret=SECRET, **headers):
    return api.post(f"/api/v1/webhooks/culqi/{secret}/", event, format="json", **headers)


def pending_culqi_payment(order, external_id="chr_test_9"):
    return Payment.objects.create(
        pedido=order, proveedor="culqi", metodo="tarjeta", external_id=external_id, monto=order.amount_due(),
        idempotency_key=f"k-{external_id}", estado=Payment.Estado.PENDIENTE,
    )


# --- Cobro con tarjeta -------------------------------------------------------

def test_cobro_aprobado_paga_el_pedido_con_monto_del_servidor_y_no_guarda_datos_de_tarjeta(api, monkeypatch):
    _, (v,) = make_product(stock_units=1)
    order = make_order(v, precio=Decimal("180.50"))
    sent = {}

    def fake(self, payload):
        sent.update(payload)
        return ok_charge(payload["amount"])

    monkeypatch.setattr(CulqiClient, "create_charge", fake)
    r = api.post(charge_url(order), {"token_id": "tkn_test_abc", "idempotency_key": "k1", "email": "a@b.com", "monto": 1, "amount": 1}, format="json")
    assert r.status_code == 201 and r.json() == {"estado": "aprobado", "pedido_estado": "PAGADO"}
    assert sent["amount"] == 18050 and sent["currency_code"] == "PEN" and sent["source_id"] == "tkn_test_abc"
    payment = Payment.objects.get()
    assert payment.monto == Decimal("180.50") and payment.external_id == "chr_test_1"
    assert "source" not in payment.payload and "411111" not in json.dumps(payment.payload)
    v.refresh_from_db()
    assert v.stock_disponible == 0 and stock.audit_stock() == []


def test_cobro_rechazado_deja_el_pedido_pendiente_y_la_reserva_activa(api, monkeypatch):
    _, (v,) = make_product(stock_units=1)
    order = make_order(v)

    def boom(self, payload):
        raise CulqiError("rechazado", status=400, body={"user_message": "Tarjeta sin fondos"})

    monkeypatch.setattr(CulqiClient, "create_charge", boom)
    r = api.post(charge_url(order), {"token_id": "tkn", "idempotency_key": "k2"}, format="json")
    assert r.status_code == 402 and "sin fondos" in r.json()["detail"]
    order.refresh_from_db()
    assert order.estado == E.PENDIENTE_PAGO and order.reservas.filter(estado="activa").exists()


def test_reintentar_con_la_misma_clave_no_cobra_dos_veces(api, monkeypatch):
    _, (v,) = make_product(stock_units=1)
    order = make_order(v)
    calls = []
    monkeypatch.setattr(CulqiClient, "create_charge", lambda self, p: calls.append(p) or ok_charge(p["amount"]))
    first = api.post(charge_url(order), {"token_id": "tkn", "idempotency_key": "misma"}, format="json")
    second = api.post(charge_url(order), {"token_id": "tkn", "idempotency_key": "misma"}, format="json")
    assert first.status_code == 201 and second.status_code in (201, 409)
    assert len(calls) == 1 and Payment.objects.count() == 1


def test_sin_llave_secreta_el_pago_con_tarjeta_no_esta_disponible(api, settings):
    settings.CULQI_SECRET_KEY = ""
    _, (v,) = make_product(stock_units=1)
    order = make_order(v)
    assert api.post(charge_url(order), {"token_id": "t", "idempotency_key": "k"}, format="json").status_code == 503


def test_un_cobro_no_exitoso_no_aprueba(api, monkeypatch):
    _, (v,) = make_product(stock_units=1)
    order = make_order(v)
    monkeypatch.setattr(CulqiClient, "create_charge", lambda self, p: {**ok_charge(p["amount"]), "outcome": {"type": "rechazada", "user_message": "No"}})
    assert api.post(charge_url(order), {"token_id": "t", "idempotency_key": "k"}, format="json").status_code == 402
    order.refresh_from_db()
    assert order.estado == E.PENDIENTE_PAGO


def test_la_unidad_en_centimos():
    assert to_cents(Decimal("99.99")) == 9999 and to_cents(Decimal("10")) == 1000


def test_la_pasarela_activa_solo_se_ofrece_con_llaves(api, settings):
    assert api.get("/api/v1/store-settings/public/").json()["payments_provider"] == "culqi"
    assert api.get("/api/v1/store-settings/public/").json()["culqi_public_key"] == "pk_test_x"
    settings.CULQI_SECRET_KEY = ""
    data = api.get("/api/v1/store-settings/public/").json()
    assert data["payments_provider"] == "manual_yape_plin" and data["culqi_public_key"] == ""
    assert "sk_test" not in json.dumps(data)


def test_crear_orden_de_pago_culqi(api, monkeypatch):
    _, (v,) = make_product(stock_units=1)
    order = make_order(v, precio=Decimal("120"))
    sent = {}
    monkeypatch.setattr(CulqiClient, "create_order", lambda self, p: sent.update(p) or {"id": "ord_test_1", "amount": p["amount"], "state": "pending"})
    r = api.post(f"/api/v1/orders/{order.public_token}/payments/culqi/order/", {"idempotency_key": "o1"}, format="json")
    assert r.status_code == 201 and r.json()["culqi_order_id"] == "ord_test_1"
    assert sent["amount"] == 12000 and sent["confirm"] is False


# --- Webhooks ----------------------------------------------------------------

def test_webhook_con_secreto_incorrecto_responde_404(api):
    assert webhook(api, {"id": "evn_1", "type": "charge.creation.succeeded", "data": {"id": "x"}}, secret="otro").status_code == 404


def test_webhook_aprueba_solo_tras_consultar_el_estado_real(api, monkeypatch):
    _, (v,) = make_product(stock_units=1)
    order = make_order(v, precio=Decimal("200"))
    payment = pending_culqi_payment(order)
    monkeypatch.setattr(CulqiClient, "get_charge", lambda self, cid: ok_charge(20000, id=cid))
    r = webhook(api, {"object": "event", "id": "evn_1", "type": "charge.creation.succeeded", "data": json.dumps({"id": "chr_test_9"})})
    assert r.status_code == 200 and r.json()["resultado"] == "aprobado"
    payment.refresh_from_db()
    order.refresh_from_db()
    assert payment.estado == "aprobado" and order.estado == E.PAGADO
    assert PaymentEvent.objects.get().procesado is True


def test_webhook_es_idempotente(api, monkeypatch):
    _, (v,) = make_product(stock_units=1)
    order = make_order(v, precio=Decimal("200"))
    pending_culqi_payment(order)
    calls = []
    monkeypatch.setattr(CulqiClient, "get_charge", lambda self, cid: calls.append(cid) or ok_charge(20000, id=cid))
    event = {"id": "evn_dup", "type": "charge.creation.succeeded", "data": {"id": "chr_test_9"}}
    assert webhook(api, event).json()["resultado"] == "aprobado"
    assert webhook(api, event).json()["resultado"] == "duplicado"
    assert PaymentEvent.objects.count() == 1 and len(calls) == 1
    assert Order.objects.get(pk=order.pk).historial.filter(estado_nuevo="PAGADO").count() == 1


def test_un_evento_falso_no_aprueba_nada(api, monkeypatch):
    _, (v,) = make_product(stock_units=1)
    order = make_order(v, precio=Decimal("200"))
    payment = pending_culqi_payment(order)
    monkeypatch.setattr(CulqiClient, "get_charge", lambda self, cid: {"id": cid, "amount": 20000, "currency_code": "PEN", "outcome": {"type": "rechazada"}})
    r = webhook(api, {"id": "evn_fake", "type": "charge.creation.succeeded", "data": {"id": "chr_test_9"}})
    assert r.json()["resultado"] == "no_exitoso"
    payment.refresh_from_db()
    assert payment.estado == Payment.Estado.PENDIENTE and Order.objects.get(pk=order.pk).estado == E.PENDIENTE_PAGO


def test_monto_distinto_al_esperado_no_aprueba(api, monkeypatch):
    _, (v,) = make_product(stock_units=1)
    order = make_order(v, precio=Decimal("200"))
    payment = pending_culqi_payment(order)
    monkeypatch.setattr(CulqiClient, "get_charge", lambda self, cid: ok_charge(100, id=cid))  # S/ 1 en vez de S/ 200
    assert webhook(api, {"id": "evn_m", "type": "charge.creation.succeeded", "data": {"id": "chr_test_9"}}).json()["resultado"] == "monto_no_coincide"
    payment.refresh_from_db()
    assert payment.estado == Payment.Estado.PENDIENTE


def test_si_culqi_no_responde_se_pide_reintento_y_el_evento_queda_sin_procesar(api, monkeypatch):
    _, (v,) = make_product(stock_units=1)
    order = make_order(v, precio=Decimal("200"))
    pending_culqi_payment(order)

    def down(self, cid):
        raise CulqiError("sin conexión", status=0)

    monkeypatch.setattr(CulqiClient, "get_charge", down)
    event = {"id": "evn_retry", "type": "charge.creation.succeeded", "data": {"id": "chr_test_9"}}
    assert webhook(api, event).status_code == 503
    assert PaymentEvent.objects.get().procesado is False
    monkeypatch.setattr(CulqiClient, "get_charge", lambda self, cid: ok_charge(20000, id=cid))
    assert webhook(api, event).json()["resultado"] == "aprobado"  # el reintento sí se procesa


def test_webhook_de_orden_pagada_aprueba_y_expirada_marca_el_pago(api, monkeypatch):
    _, (v,) = make_product(stock_units=2)
    paid = make_order(v, precio=Decimal("100"))
    pending_culqi_payment(paid, "ord_test_paid")
    dead = make_order(v, precio=Decimal("100"))
    pending_culqi_payment(dead, "ord_test_dead")
    states = {"ord_test_paid": ("paid", 10000), "ord_test_dead": ("expired", 10000)}
    monkeypatch.setattr(CulqiClient, "get_order", lambda self, oid: {"id": oid, "state": states[oid][0], "amount": states[oid][1], "currency_code": "PEN"})
    assert webhook(api, {"id": "evn_o1", "type": "order.status.changed", "data": {"id": "ord_test_paid"}}).json()["resultado"] == "aprobado"
    assert webhook(api, {"id": "evn_o2", "type": "order.status.changed", "data": {"id": "ord_test_dead"}}).json()["resultado"] == "expirado"
    assert Order.objects.get(pk=paid.pk).estado == E.PAGADO
    assert Payment.objects.get(external_id="ord_test_dead").estado == Payment.Estado.EXPIRADO


def test_webhook_con_basic_auth_configurada(api, settings, monkeypatch):
    settings.CULQI_WEBHOOK_BASIC_USER = "culqi"
    settings.CULQI_WEBHOOK_BASIC_PASSWORD = "clave"
    event = {"id": "evn_b", "type": "otro.evento", "data": {"id": "x"}}
    assert webhook(api, event).status_code == 404
    good = "Basic " + base64.b64encode(b"culqi:clave").decode()
    assert webhook(api, event, HTTP_AUTHORIZATION=good).json()["resultado"] == "ignorado"


def test_evento_malformado_responde_400(api):
    assert webhook(api, {"type": "charge.creation.succeeded", "data": {"id": "x"}}).status_code == 400
    assert webhook(api, {"id": "e", "type": "charge.creation.succeeded", "data": "no-json"}).status_code == 400


def test_pago_con_tarjeta_tras_expirar_reserva_de_nuevo_si_hay_stock(api, monkeypatch):
    from datetime import timedelta

    from django.utils import timezone

    _, (v,) = make_product(stock_units=1)
    order = make_order(v, precio=Decimal("100"))
    Order.objects.filter(pk=order.pk).update(expira_en=timezone.now() - timedelta(minutes=1))
    orders.expire_pending_orders()
    pending_culqi_payment(order)
    monkeypatch.setattr(CulqiClient, "get_charge", lambda self, cid: ok_charge(10000, id=cid))
    assert webhook(api, {"id": "evn_late", "type": "charge.creation.succeeded", "data": {"id": "chr_test_9"}}).json()["resultado"] == "aprobado"
    assert Order.objects.get(pk=order.pk).estado == E.PAGADO and stock.audit_stock() == []


def test_pago_aprobado_sin_stock_queda_para_revision_manual(api, monkeypatch):
    from datetime import timedelta

    from django.utils import timezone

    _, (v,) = make_product(stock_units=1)
    first = make_order(v, precio=Decimal("100"))
    Order.objects.filter(pk=first.pk).update(expira_en=timezone.now() - timedelta(minutes=1))
    orders.expire_pending_orders()
    make_order(v, precio=Decimal("100"))  # otra clienta se llevó la unidad
    pending_culqi_payment(first)
    monkeypatch.setattr(CulqiClient, "get_charge", lambda self, cid: ok_charge(10000, id=cid))
    assert webhook(api, {"id": "evn_nostock", "type": "charge.creation.succeeded", "data": {"id": "chr_test_9"}}).json()["resultado"] == "requiere_revision"
    assert Order.objects.get(pk=first.pk).estado == E.EXPIRADO  # no se confirma sin stock


# --- Pedidos por encargo: adelanto y saldo ------------------------------------

def preorder(price=Decimal("200"), pct=Decimal("40")):
    cfg = StoreSettings.load()
    cfg.pct_adelanto = pct
    cfg.save()
    product, (v,) = make_product(stock_units=0, precio=price)
    Product.objects.filter(pk=product.pk).update(tipo_venta="por_encargo")
    order = make_order(v, reserve=False, precio=price)
    Order.objects.filter(pk=order.pk).update(tipo_venta="por_encargo", adelanto_pen=price * pct / 100, saldo_pen=price - price * pct / 100)
    order.refresh_from_db()
    return order


def png():
    import io

    from PIL import Image

    buf = io.BytesIO()
    Image.new("RGB", (4, 4), "pink").save(buf, "PNG")
    return SimpleUploadedFile("c.png", buf.getvalue(), content_type="image/png")


def test_el_adelanto_pasa_el_pedido_a_pagado_y_queda_saldo(api):
    order = preorder()
    assert order.amount_due() == Decimal("80.00")
    r = api.post(f"/api/v1/orders/{order.public_token}/payments/manual/", {"comprobante": png(), "metodo": "yape"}, format="multipart")
    assert r.json()["monto"] == "80.00"
    payments.approve_payment(Payment.objects.get())
    order.refresh_from_db()
    assert order.estado == E.PAGADO and order.saldo_pendiente == Decimal("120.00")
    assert Payment.objects.get().es_adelanto is True


def test_el_saldo_se_paga_cuando_el_pedido_llega_a_lima(api):
    order = preorder()
    adv = Payment.objects.create(pedido=order, proveedor="manual_yape_plin", metodo="yape", monto=Decimal("80"), es_adelanto=True, idempotency_key="a", estado="en_revision")
    payments.approve_payment(adv)
    # Antes de que llegue, ya hay saldo por pagar pero el pedido sigue en curso.
    orders.transition(order, E.COMPRADO)
    orders.transition(order, E.EN_CAMINO)
    orders.transition(order, E.EN_LIMA)
    track = api.get(f"/api/v1/orders/track/{order.public_token}/").json()
    assert track["por_pagar"] == "120.00"
    r = api.post(f"/api/v1/orders/{order.public_token}/payments/manual/", {"comprobante": png(), "metodo": "plin"}, format="multipart")
    assert r.status_code == 201 and r.json()["monto"] == "120.00"
    saldo = Payment.objects.get(es_adelanto=False)
    payments.approve_payment(saldo)
    order.refresh_from_db()
    assert order.saldo_pendiente == 0 and order.amount_due() == 0
    assert api.post(f"/api/v1/orders/{order.public_token}/payments/manual/", {"comprobante": png(), "metodo": "plin"}, format="multipart").status_code == 409
    orders.transition(order, E.ENTREGADO)
    assert Order.objects.get(pk=order.pk).estado == E.ENTREGADO


def test_un_pedido_de_stock_local_pagado_no_tiene_saldo(api):
    _, (v,) = make_product(stock_units=1)
    order = make_order(v)
    orders.transition(order, E.PAGADO)
    order.refresh_from_db()
    assert order.amount_due() == 0


def test_el_evento_para_n8n_incluye_datos_para_avisar_por_whatsapp():
    from apps.integrations.models import WebhookOutbox

    _, (v,) = make_product(stock_units=1)
    order = make_order(v)
    orders.transition(order, E.PAGADO)
    payload = WebhookOutbox.objects.filter(evento="order.status_changed").last().payload
    assert payload["nuevo"] == "PAGADO" and payload["telefono"] and payload["cliente"] and "token" in payload
