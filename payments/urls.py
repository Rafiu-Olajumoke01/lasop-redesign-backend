from django.urls import path
from .views import (
    InitiatePaymentView,
    PaymentStatusView,
    ConfirmClickedView,
    PaystackWebhookView,
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
    path("payments/webhook/", PaystackWebhookView.as_view(), name="payment-webhook"),
]