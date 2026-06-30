from django.contrib import admin
from django.utils import timezone
from .models import Payment


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = (
        "tx_ref", "application", "method", "payment_type",
        "amount", "status", "created_at",
    )
    list_filter = ("status", "method", "payment_type")
    search_fields = (
        "tx_ref", "application__student__email",
        "application__student__first_name", "application__student__last_name",
    )
    readonly_fields = (
        "id", "tx_ref", "flw_ref", "created_at", "updated_at",
        "raw_webhook_payload",
    )
    actions = ["mark_as_paid"]

    @admin.action(description="Mark selected payments as Paid (confirms receipt)")
    def mark_as_paid(self, request, queryset):
        updated = 0
        for payment in queryset:
            if payment.status == Payment.Status.PAID:
                continue
            payment.status = Payment.Status.PAID
            payment.confirmed_amount = payment.amount
            payment.paid_at = timezone.now()
            payment.reviewed_by = request.user
            payment.reviewed_at = timezone.now()
            payment.save(update_fields=[
                "status", "confirmed_amount", "paid_at",
                "reviewed_by", "reviewed_at",
            ])
            updated += 1
        self.message_user(request, f"{updated} payment(s) marked as paid.")