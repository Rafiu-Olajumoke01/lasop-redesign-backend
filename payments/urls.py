"""
payments/urls.py

Add this to your main urls.py with:
    path("api/", include("payments.urls")),
"""
from django.urls import path
from .views import (
    InitiatePaymentView,
    PaymentStatusView,
    ConfirmClickedView,
    FlutterwaveWebhookView,
)

urlpatterns = [
    path(
        "applications/<uuid:application_id>/payments/initiate/",
        InitiatePaymentView.as_view(),
        name="payment-initiate",
    ),
    path(
        "applications/<uuid:application_id>/payments/status/",
        PaymentStatusView.as_view(),
        name="payment-status",
    ),
    path(
        "applications/<uuid:application_id>/payments/confirm-clicked/",
        ConfirmClickedView.as_view(),
        name="payment-confirm-clicked",
    ),
    # No application_id here on purpose - Flutterwave only knows this one fixed URL
    path("payments/webhook/", FlutterwaveWebhookView.as_view(), name="payment-webhook"),
]