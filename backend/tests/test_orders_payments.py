from datetime import timedelta

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from django.utils import timezone

from apps.inventory import services as stock
from apps.inventory.models import StockReservation
from apps.integrations.models import WebhookOutbox
from apps.orders import services as orders
from apps.orders.models import Order
from apps.payments import services as payments
from apps.payments.models import Payment
from apps.payments.providers import get_provider
from tests.factories import make_order, make_product

pytestmark = pytest.mark.django_db
E = Order.Estado


def _expire(order):
    Order.objects.filter(pk=order.pk).update(expira_en=timezone.now() - timedelta(minutes=1))


def test_flujo_feliz_con_historial_y_evento_para_n8n():
    _, (v,) = make_product(stock_units=1)
    order = make_order(v)
    orders.transition(order, E.PAGADO, nota="Yape verificado")
    orders.transition(order, E.EN_LIMA)
    order = orders.transition(order, E.ENTREGADO)
    v.refresh_from_db()
    assert order.estado == E.ENTREGADO
    assert (v.stock_disponible, v.stock_reservado) == (0, 0)
    assert list(order.historial.values_list("estado_nuevo", flat=True)) == ["PAGADO", "EN_LIMA", "ENTREGADO"]
    assert WebhookOutbox.objects.filter(evento="order.status_changed").count() == 3
    assert stock.audit_stock() == []


def test_transicion_invalida_se_rechaza():
    _, (v,) = make_product(stock_units=1)
    order = make_order(v)
    with pytest.raises(orders.OrderError):
        orders.transition(order, E.ENTREGADO)
    orders.transition(order, E.CANCELADO)
    with pytest.raises(orders.OrderError):
        orders.transition(order, E.PAGADO)


def test_cancelar_antes_de_pagar_libera_la_reserva():
    _, (v,) = make_product(stock_units=1)
    order = make_order(v)
    orders.transition(order, E.CANCELADO)
    v.refresh_from_db()
    assert v.stock_reservado == 0
    assert not order.reservas.filter(estado=StockReservation.Estado.ACTIVA).exists()


def test_cancelar_un_pedido_pagado_devuelve_la_unidad_al_inventario():
    _, (v,) = make_product(stock_units=1)
    order = make_order(v)
    orders.transition(order, E.PAGADO)
    v.refresh_from_db()
    assert v.stock_disponible == 0
    orders.transition(order, E.CANCELADO)
    v.refresh_from_db()
    assert v.stock_disponible == 1
    assert stock.audit_stock() == []


def test_pedido_expirado_libera_el_stock():
    _, (v,) = make_product(stock_units=1)
    order = make_order(v)
    _expire(order)
    assert orders.expire_pending_orders() == 1
    order.refresh_from_db()
    v.refresh_from_db()
    assert order.estado == E.EXPIRADO
    assert (v.stock_disponible, v.stock_reservado, v.disponible) == (1, 0, 1)


def test_pedido_vigente_no_expira():
    _, (v,) = make_product(stock_units=1)
    order = make_order(v, minutes=15)
    assert orders.expire_pending_orders() == 0
    order.refresh_from_db()
    assert order.estado == E.PENDIENTE_PAGO


def test_pedido_con_comprobante_en_revision_no_expira():
    _, (v,) = make_product(stock_units=1)
    order = make_order(v)
    get_provider().create_payment(order, idempotency_key="k-rev", comprobante=SimpleUploadedFile("c.png", b"x"))
    _expire(order)
    assert orders.expire_pending_orders() == 0


def test_tras_expirar_la_unidad_se_puede_vender_a_otra_clienta():
    _, (v,) = make_product(stock_units=1)
    first = make_order(v)
    _expire(first)
    orders.expire_pending_orders()
    second = make_order(v)
    assert second.reservas.filter(estado="activa").count() == 1


def test_pago_aprobado_despues_de_expirar_reserva_de_nuevo_si_hay_stock():
    _, (v,) = make_product(stock_units=1)
    order = make_order(v)
    _expire(order)
    orders.expire_pending_orders()
    orders.transition(order, E.PAGADO)
    v.refresh_from_db()
    assert v.stock_disponible == 0
    assert stock.audit_stock() == []


def test_pago_tardio_sin_stock_no_confirma_y_pide_reembolso():
    _, (v,) = make_product(stock_units=1)
    first = make_order(v)
    _expire(first)
    orders.expire_pending_orders()
    make_order(v)  # otra clienta se llevó la unidad
    with pytest.raises(orders.OrderError, match="reembolsar"):
        orders.transition(first, E.PAGADO)
    first.refresh_from_db()
    assert first.estado == E.EXPIRADO


def test_aprobar_pago_manual_pasa_el_pedido_a_pagado():
    _, (v,) = make_product(stock_units=1)
    order = make_order(v)
    payment = get_provider().create_payment(order, idempotency_key="k1", comprobante=SimpleUploadedFile("c.png", b"x"))
    assert payment.monto == order.total_pen
    assert payment.estado == Payment.Estado.EN_REVISION
    payments.approve_payment(payment)
    order.refresh_from_db()
    assert order.estado == E.PAGADO


def test_el_monto_del_pago_lo_define_el_servidor():
    _, (v,) = make_product(stock_units=1)
    order = make_order(v, precio=250)
    payment = get_provider().create_payment(order, idempotency_key="k2", monto=1)  # monto del cliente se ignora
    assert payment.monto == 250


def test_misma_idempotency_key_no_duplica_el_pago():
    _, (v,) = make_product(stock_units=1)
    order = make_order(v)
    a = get_provider().create_payment(order, idempotency_key="k3")
    b = get_provider().create_payment(order, idempotency_key="k3")
    assert a.pk == b.pk
    assert Payment.objects.count() == 1


def test_un_pago_no_se_aprueba_dos_veces():
    _, (v,) = make_product(stock_units=1)
    order = make_order(v)
    payment = get_provider().create_payment(order, idempotency_key="k4", comprobante=SimpleUploadedFile("c.png", b"x"))
    payments.approve_payment(payment)
    with pytest.raises(payments.PaymentError):
        payments.approve_payment(payment)


def test_pago_rechazado_deja_el_pedido_pendiente():
    _, (v,) = make_product(stock_units=1)
    order = make_order(v)
    payment = get_provider().create_payment(order, idempotency_key="k5", comprobante=SimpleUploadedFile("c.png", b"x"))
    payments.reject_payment(payment, nota="Monto incorrecto")
    order.refresh_from_db()
    assert order.estado == E.PENDIENTE_PAGO


def test_pasarela_no_implementada_falla_claro():
    with pytest.raises(NotImplementedError):
        get_provider("izipay")
