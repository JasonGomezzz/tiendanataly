from django.urls import include, path
from rest_framework.routers import SimpleRouter

from apps.accounts import views as account_views
from apps.cart import api as cart_api
from apps.catalog import api as catalog_api
from apps.core import staff_api
from apps.core.api import PublicStoreSettingsView
from apps.legal.api import ComplaintCreateView
from apps.orders.api import CheckoutView, MyOrderViewSet, OrderWhatsappView, TrackOrderView
from apps.payments.api import CulqiChargeView, CulqiOrderView, CulqiWebhookView, ManualPaymentView
from apps.shipping.api import ShippingZoneViewSet

router = SimpleRouter()
router.register("products", catalog_api.ProductViewSet, basename="product")
router.register("categories", catalog_api.CategoryViewSet, basename="category")
router.register("brands", catalog_api.BrandViewSet, basename="brand")
router.register("collections", catalog_api.CollectionViewSet, basename="collection")
router.register("shipping/zones", ShippingZoneViewSet, basename="shipping-zone")
router.register("me/addresses", account_views.AddressViewSet, basename="my-address")
router.register("me/orders", MyOrderViewSet, basename="my-order")

auth_patterns = [
    path("csrf/", account_views.CsrfView.as_view()),
    path("register/", account_views.RegisterView.as_view()),
    path("login/", account_views.LoginView.as_view()),
    path("logout/", account_views.LogoutView.as_view()),
    path("password/reset/", account_views.PasswordResetRequestView.as_view()),
    path("password/reset/confirm/", account_views.PasswordResetConfirmView.as_view()),
]

urlpatterns = [
    path("auth/", include(auth_patterns)),
    path("me/", account_views.MeView.as_view()),
    path("store-settings/public/", PublicStoreSettingsView.as_view()),
    path("variants/<int:variant_id>/stock-alerts/", catalog_api.StockAlertCreateView.as_view()),
    path("cart/", cart_api.CartView.as_view()),
    path("cart/items/", cart_api.CartItemsView.as_view()),
    path("cart/items/<int:pk>/", cart_api.CartItemDetailView.as_view()),
    path("cart/merge/", cart_api.CartMergeView.as_view()),
    path("checkout/", CheckoutView.as_view()),
    path("orders/track/<uuid:public_token>/", TrackOrderView.as_view()),
    path("orders/<uuid:public_token>/whatsapp-message/", OrderWhatsappView.as_view()),
    path("orders/<uuid:public_token>/payments/manual/", ManualPaymentView.as_view()),
    path("orders/<uuid:public_token>/payments/culqi/charge/", CulqiChargeView.as_view()),
    path("orders/<uuid:public_token>/payments/culqi/order/", CulqiOrderView.as_view()),
    path("webhooks/culqi/<str:secret>/", CulqiWebhookView.as_view()),
    path("complaints/", ComplaintCreateView.as_view()),
    # Panel /admin (Next.js): solo Administradora, Staff y superusuario, con permisos por vista
    path("admin/me/", staff_api.MeStaffView.as_view()),
    path("admin/meta/", staff_api.MetaView.as_view()),
    path("admin/dashboard/", staff_api.DashboardView.as_view()),
    path("admin/products/", staff_api.ProductListView.as_view()),
    path("admin/products/<int:pk>/", staff_api.ProductDetailView.as_view()),
    path("admin/products/<int:pk>/images/", staff_api.ProductImagesView.as_view()),
    path("admin/products/<int:pk>/variants/", staff_api.VariantCreateView.as_view()),
    path("admin/products/<int:pk>/<str:action>/", staff_api.ProductStateView.as_view()),
    path("admin/variants/<int:pk>/", staff_api.VariantDetailView.as_view()),
    path("admin/variants/<int:pk>/adjust-stock/", staff_api.VariantStockView.as_view()),
    path("admin/pricing/calculate/", staff_api.PriceCalcView.as_view()),
    path("admin/exchange-rates/", staff_api.ExchangeRateView.as_view()),
    path("admin/store-settings/", staff_api.StoreSettingsView.as_view()),
    path("admin/orders/", staff_api.OrderListView.as_view()),
    path("admin/orders/<int:pk>/", staff_api.OrderDetailView.as_view()),
    path("admin/orders/<int:pk>/transition/", staff_api.OrderTransitionView.as_view()),
    path("admin/payments/<int:pk>/<str:action>/", staff_api.PaymentActionView.as_view()),
    path("admin/audit-log/", staff_api.AuditLogView.as_view()),
    path("admin/bank-accounts/", staff_api.BankAccountListView.as_view()),
    path("admin/bank-accounts/<int:pk>/", staff_api.BankAccountDetailView.as_view()),
    path("", include(router.urls)),
]
