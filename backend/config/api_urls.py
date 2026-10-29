from django.urls import include, path
from rest_framework.routers import SimpleRouter

from apps.accounts import views as account_views
from apps.cart import api as cart_api
from apps.catalog import api as catalog_api
from apps.core.api import PublicStoreSettingsView
from apps.legal.api import ComplaintCreateView
from apps.orders.api import CheckoutView, MyOrderViewSet, OrderWhatsappView, TrackOrderView
from apps.payments.api import ManualPaymentView
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
    path("complaints/", ComplaintCreateView.as_view()),
    path("", include(router.urls)),
]
