"""
payments/models.py

A Payment record is created each time a student initiates a bank transfer
for an Application. Re-initiating (after expiry) creates a NEW Payment row
rather than mutating the old one, so you keep a full audit trail of every
attempt.
"""
import uuid
from django.db import models
from django.utils import timezone
from datetime import timedelta

from applications.models import Application  # adjust import path to match your project


class Payment(models.Model):
    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        AWAITING_CONFIRMATION = "awaiting_confirmation", "Awaiting Confirmation"  # student clicked "I have made payment"
        PAID = "paid", "Paid"
        EXPIRED = "expired", "Expired"
        FAILED = "failed", "Failed"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    application = models.ForeignKey(
        Application, on_delete=models.CASCADE, related_name="payments"
    )

    # Flutterwave references
    tx_ref = models.CharField(max_length=100, unique=True)  # our reference, sent to Flutterwave
    flw_ref = models.CharField(max_length=100, blank=True, null=True)  # Flutterwave's own reference, from webhook
    virtual_account_number = models.CharField(max_length=30, blank=True, null=True)
    virtual_bank_name = models.CharField(max_length=100, blank=True, null=True)

    amount = models.DecimalField(max_digits=12, decimal_places=2)
    status = models.CharField(max_length=30, choices=Status.choices, default=Status.PENDING)

    expires_at = models.DateTimeField()
    confirmed_clicked_at = models.DateTimeField(blank=True, null=True)  # when student clicked "I have made payment"
    paid_at = models.DateTimeField(blank=True, null=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    # raw webhook payload, kept for debugging/audit
    raw_webhook_payload = models.JSONField(blank=True, null=True)

    class Meta:
        ordering = ["-created_at"]

    def save(self, *args, **kwargs):
        if not self.expires_at:
            self.expires_at = timezone.now() + timedelta(minutes=30)
        if not self.tx_ref:
            self.tx_ref = f"LASOP-{uuid.uuid4().hex[:12].upper()}"
        super().save(*args, **kwargs)

    @property
    def is_expired(self):
        return self.status == self.Status.PENDING and timezone.now() > self.expires_at

    @property
    def seconds_remaining(self):
        remaining = (self.expires_at - timezone.now()).total_seconds()
        return max(0, int(remaining))

    def mark_expired_if_needed(self):
        if self.is_expired:
            self.status = self.Status.EXPIRED
            self.save(update_fields=["status", "updated_at"])
        return self.status

    def __str__(self):
        return f"{self.tx_ref} - {self.application_id} - {self.status}"