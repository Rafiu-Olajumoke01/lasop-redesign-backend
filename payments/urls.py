from django.urls import path
from .views import (
    InitiatePaymentView,
    PaymentStatusView,
    ConfirmClickedView,
    PaystackWebhookView,
    ManualInitiatePaymentView,
    ManualConfirmClickedView,
    AdminConfirmPaymentView,
)

urlpatterns = [
    path(
        "applications/<int:application_id>/payments/initiate/",
        InitiatePaymentView.as_view(),
        name="payment-initiate",
    ),
    path(
        "applications/<int:application_id>/payments/status/",
        PaymentStatusView.as_view(),
        name="payment-status",
    ),
    path(
        "applications/<int:application_id>/payments/confirm-clicked/",
        ConfirmClickedView.as_view(),
        name="payment-confirm-clicked",
    ),
    path(
        "applications/<int:application_id>/payments/manual/initiate/",
        ManualInitiatePaymentView.as_view(),
        name="payment-manual-initiate",
    ),
    path(
        "applications/<int:application_id>/payments/manual/confirm-clicked/",
        ManualConfirmClickedView.as_view(),
        name="payment-manual-confirm-clicked",
    ),
    path(
        "applications/<int:application_id>/payments/admin-confirm/",
        AdminConfirmPaymentView.as_view(),
        name="payment-admin-confirm",
    ),
    path("payments/webhook/", PaystackWebhookView.as_view(), name="payment-webhook"),
]