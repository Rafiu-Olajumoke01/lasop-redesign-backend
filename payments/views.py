
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status as http_status
from rest_framework.permissions import IsAuthenticated, AllowAny
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from django.shortcuts import get_object_or_404
from rest_framework.permissions import IsAdminUser
import logging

from applications.models import Application
from .models import Payment
from . import paystack

logger = logging.getLogger(__name__)

CALLBACK_URL = "https://lasop.net"


class InitiatePaymentView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, application_id):
        application = get_object_or_404(Application, id=application_id, student=request.user)

        # Return existing active payment if one exists and hasn't expired
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
            result = paystack.initialize_transaction(
                reference=payment.tx_ref,
                amount=payment.amount,
                email=request.user.email,
                callback_url=CALLBACK_URL,
            )
        except paystack.PaystackError as e:
            payment.status = Payment.Status.FAILED
            payment.save(update_fields=["status"])
            logger.error("Paystack transaction initialization failed: %s", e)
            return Response(
                {"detail": "Could not initiate payment. Please try again shortly."},
                status=http_status.HTTP_502_BAD_GATEWAY,
            )

        # Store the authorization_url in flw_ref field to avoid new migration
        payment.flw_ref = result["authorization_url"]
        payment.save(update_fields=["flw_ref"])

        return Response(self._serialize(payment), status=http_status.HTTP_201_CREATED)

    @staticmethod
    def _serialize(payment):
        return {
            "id": str(payment.id),
            "status": payment.status,
            "amount": str(payment.amount),
            "authorization_url": payment.flw_ref,  # stored here to avoid migration
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
            "authorization_url": payment.flw_ref,
            "expires_at": payment.expires_at.isoformat(),
            "seconds_remaining": payment.seconds_remaining,
        })


class ConfirmClickedView(APIView):
    """Student clicked 'I have completed payment'. This only changes UI state —
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


class PaystackWebhookView(APIView):
    """
    Public endpoint - Paystack calls this directly, no user auth available.
    Security: verify 'x-paystack-signature' header + re-verify transaction server-to-server.
    """
    permission_classes = [AllowAny]

    @csrf_exempt
    def post(self, request):
        if not paystack.verify_webhook_signature(request):
            logger.warning("Rejected webhook with invalid signature")
            return Response(status=401)

        payload = request.data
        event = payload.get("event", "")

        # Only process successful charge events
        if event not in ("charge.success", "transfer.success"):
            return Response(status=200)

        tx_ref = payload.get("data", {}).get("reference")

        if not tx_ref:
            return Response(status=400)

        payment = Payment.objects.filter(tx_ref=tx_ref).first()
        if not payment:
            logger.warning("Webhook for unknown tx_ref: %s", tx_ref)
            return Response(status=200)

        payment.raw_webhook_payload = payload
        payment.save(update_fields=["raw_webhook_payload"])

        # Re-verify with Paystack directly
        verification = paystack.verify_transaction(tx_ref)
        verified_status = verification.get("data", {}).get("status")
        verified_amount = verification.get("data", {}).get("amount", 0)  # in kobo

        try:
            amount_in_kobo = int(verified_amount)
            expected_kobo = int(float(payment.amount) * 100)
        except (ValueError, TypeError):
            logger.error("Could not parse amounts for tx_ref: %s", tx_ref)
            return Response(status=200)

        if verified_status == "success" and amount_in_kobo >= expected_kobo:
            payment.status = Payment.Status.PAID
            payment.paid_at = timezone.now()
            payment.save(update_fields=["status", "paid_at"])
            logger.info("Payment marked as PAID: %s", tx_ref)
        else:
            payment.status = Payment.Status.FAILED
            payment.save(update_fields=["status"])
            logger.warning(
                "Payment verification failed for %s — status: %s, amount: %s kobo (expected %s)",
                tx_ref, verified_status, amount_in_kobo, expected_kobo
            )

        return Response(status=200)
    

class ManualInitiatePaymentView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, application_id):
        application = get_object_or_404(Application, id=application_id, student=request.user)

        payment_type = request.data.get("payment_type")
        amount = request.data.get("amount")

        if payment_type not in (Payment.PaymentType.FULL, Payment.PaymentType.PART):
            return Response({"detail": "Invalid payment_type."}, status=400)

        try:
            amount = float(amount)
        except (TypeError, ValueError):
            return Response({"detail": "Invalid amount."}, status=400)

        if amount <= 0:
            return Response({"detail": "Amount must be greater than 0."}, status=400)

        if payment_type == Payment.PaymentType.FULL and amount < float(application.course.fee):
            return Response(
                {"detail": "Full payment amount cannot be less than the course fee."},
                status=400,
            )

        # Reuse an existing pending/in-review manual payment instead of
        # creating a duplicate row if the student re-opens "Pay Now"
        # before admin has confirmed their first attempt.
        existing = (
            application.payments
            .filter(
                method=Payment.Method.MANUAL,
                status__in=[Payment.Status.PENDING, Payment.Status.AWAITING_CONFIRMATION],
            )
            .order_by("-created_at")
            .first()
        )

        if existing:
            existing.amount = amount
            existing.payment_type = payment_type
            existing.status = Payment.Status.PENDING
            existing.save(update_fields=["amount", "payment_type", "status"])
            payment = existing
        else:
            payment = Payment.objects.create(
                application=application,
                amount=amount,
                method=Payment.Method.MANUAL,
                payment_type=payment_type,
                status=Payment.Status.PENDING,
            )

        return Response({
            "id": str(payment.id),
            "status": payment.status,
            "amount": str(payment.amount),
            "payment_type": payment.payment_type,
        }, status=201)


class ManualConfirmClickedView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, application_id):
        application = get_object_or_404(Application, id=application_id, student=request.user)

        payment = (
            application.payments
            .filter(method=Payment.Method.MANUAL, status=Payment.Status.PENDING)
            .order_by("-created_at")
            .first()
        )

        if not payment:
            return Response(
                {"detail": "No pending manual payment found. Please start again."},
                status=404,
            )

        payment.status = Payment.Status.AWAITING_CONFIRMATION
        payment.confirmed_clicked_at = timezone.now()
        payment.save(update_fields=["status", "confirmed_clicked_at"])

        return Response({"status": payment.status})
    
class AdminConfirmPaymentView(APIView):
    permission_classes = [IsAuthenticated, IsAdminUser]

    def post(self, request, application_id):
        application = get_object_or_404(Application, id=application_id)

        payment = (
            application.payments
            .exclude(status=Payment.Status.PAID)
            .order_by("-created_at")
            .first()
        )

        if not payment:
            return Response({"detail": "No unpaid payment found for this application."}, status=404)

        confirmed_amount = request.data.get("confirmed_amount")
        if confirmed_amount is not None:
            try:
                confirmed_amount = float(confirmed_amount)
            except (TypeError, ValueError):
                return Response({"detail": "Invalid confirmed_amount."}, status=400)
        else:
            confirmed_amount = float(payment.amount)

        payment.status = Payment.Status.PAID
        payment.confirmed_amount = confirmed_amount
        payment.paid_at = timezone.now()
        payment.reviewed_by = request.user
        payment.reviewed_at = timezone.now()
        payment.save(update_fields=[
            "status", "confirmed_amount", "paid_at", "reviewed_by", "reviewed_at",
        ])

        return Response({
            "status": payment.status,
            "confirmed_amount": str(payment.confirmed_amount),
        })