"""
payments/views.py

Three endpoints:
  POST /api/applications/<application_id>/payments/initiate/
        -> creates a new Payment + virtual account, starts the 30 min timer

  GET  /api/applications/<application_id>/payments/status/
        -> frontend polls this to know current payment status + seconds_remaining

  POST /api/applications/<application_id>/payments/confirm-clicked/
        -> student clicked "I have made payment" (does NOT mark as paid, just
           flips status to awaiting_confirmation so the UI can show "verifying")

  POST /api/payments/webhook/   (no application_id - Flutterwave doesn't know our URLs)
        -> Flutterwave calls this. THIS is the only place that marks a Payment as paid.
"""
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status as http_status
from rest_framework.permissions import IsAuthenticated, AllowAny
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from django.shortcuts import get_object_or_404
import logging

from applications.models import Application  # adjust to your actual path
from .models import Payment
from . import paystack

logger = logging.getLogger(__name__)


class InitiatePaymentView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, application_id):
        application = get_object_or_404(Application, id=application_id, student=request.user)

        # If there's already a live (non-expired, non-failed) payment, reuse it
        # instead of spinning up a duplicate virtual account.
        existing = (
            application.payments
            .exclude(status__in=[Payment.Status.EXPIRED, Payment.Status.FAILED])
            .order_by("-created_at")
            .first()
        )
        if existing and not existing.is_expired:
            return Response(self._serialize(existing))

        payment = Payment.objects.create(
            application=application,
            amount=application.course.fee,
        )

        try:
            result = paystack.create_virtual_account(
                tx_ref=payment.tx_ref,
                amount=payment.amount,
                email=request.user.email,
                full_name=request.user.get_full_name() or request.user.email,
                phone="",  # Application has no phone field; add one if you collect it
            )
        except paystack.FlutterwaveError as e:
            payment.status = Payment.Status.FAILED
            payment.save(update_fields=["status"])
            logger.error("Flutterwave virtual account creation failed: %s", e)
            return Response(
                {"detail": "Could not initiate payment. Please try again shortly."},
                status=http_status.HTTP_502_BAD_GATEWAY,
            )

        payment.virtual_account_number = result["account_number"]
        payment.virtual_bank_name = result["bank_name"]
        payment.flw_ref = result["flw_ref"]
        payment.save(update_fields=["virtual_account_number", "virtual_bank_name", "flw_ref"])

        return Response(self._serialize(payment), status=http_status.HTTP_201_CREATED)

    @staticmethod
    def _serialize(payment):
        return {
            "id": str(payment.id),
            "status": payment.status,
            "amount": str(payment.amount),
            "account_number": payment.virtual_account_number,
            "bank_name": payment.virtual_bank_name,
            "expires_at": payment.expires_at.isoformat(),
            "seconds_remaining": payment.seconds_remaining,
        }


class PaymentStatusView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, application_id):
        application = get_object_or_404(Application, id=application_id, student=request.user)
        payment = application.payments.order_by("-created_at").first()

        if not payment:
            return Response({"detail": "No payment found for this application."}, status=404)

        payment.mark_expired_if_needed()

        return Response({
            "id": str(payment.id),
            "status": payment.status,
            "amount": str(payment.amount),
            "account_number": payment.virtual_account_number,
            "bank_name": payment.virtual_bank_name,
            "expires_at": payment.expires_at.isoformat(),
            "seconds_remaining": payment.seconds_remaining,
        })


class ConfirmClickedView(APIView):
    """Student clicked 'I have made payment'. This only changes UI state —
    it does NOT mark the payment as paid. The webhook is what marks it paid."""
    permission_classes = [IsAuthenticated]

    def post(self, request, application_id):
        application = get_object_or_404(Application, id=application_id, student=request.user)
        payment = application.payments.order_by("-created_at").first()

        if not payment:
            return Response({"detail": "No payment found."}, status=404)

        if payment.status == Payment.Status.EXPIRED or payment.is_expired:
            return Response({"detail": "Payment window has expired. Please retry."}, status=400)

        payment.status = Payment.Status.AWAITING_CONFIRMATION
        payment.confirmed_clicked_at = timezone.now()
        payment.save(update_fields=["status", "confirmed_clicked_at"])

        return Response({"status": payment.status})


class FlutterwaveWebhookView(APIView):
    """
    Public endpoint - Flutterwave calls this directly, no user auth available.
    Security comes from verifying the 'verif-hash' header + re-verifying the
    transaction server-to-server (never trust the webhook body alone).
    """
    permission_classes = [AllowAny]

    @csrf_exempt
    def post(self, request):
        if not paystack.verify_webhook_signature(request):
            logger.warning("Rejected webhook with invalid signature")
            return Response(status=401)

        payload = request.data
        tx_ref = payload.get("data", {}).get("tx_ref") or payload.get("txRef")
        transaction_id = payload.get("data", {}).get("id")

        if not tx_ref:
            return Response(status=400)

        payment = Payment.objects.filter(tx_ref=tx_ref).first()
        if not payment:
            logger.warning("Webhook for unknown tx_ref: %s", tx_ref)
            return Response(status=404)

        payment.raw_webhook_payload = payload
        payment.save(update_fields=["raw_webhook_payload"])

        # Re-verify with Flutterwave directly rather than trusting the payload as-is
        verification = paystack.verify_transaction(transaction_id)
        verified_status = verification.get("data", {}).get("status")
        verified_amount = verification.get("data", {}).get("amount")

        if verified_status == "successful" and float(verified_amount) >= float(payment.amount):
            payment.status = Payment.Status.PAID
            payment.paid_at = timezone.now()
            payment.save(update_fields=["status", "paid_at"])
            # Note: Application itself has no payment_status field — the Payment
            # model above is the single source of truth for status. The dashboard
            # should look up the latest Payment for an Application, not the
            # Application itself, to know if it's paid.
        else:
            payment.status = Payment.Status.FAILED
            payment.save(update_fields=["status"])

        return Response(status=200)