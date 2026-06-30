from rest_framework import serializers
from .models import Application
from courses.models import Course, Location


class LocationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Location
        fields = ['id', 'name', 'address']


class CourseSerializer(serializers.ModelSerializer):
    class Meta:
        model = Course
        fields = ['id', 'title', 'category', 'duration', 'fee']


class ApplicationSerializer(serializers.ModelSerializer):
    course_detail = CourseSerializer(source='course', read_only=True)
    location_detail = LocationSerializer(source='location', read_only=True)
    payment_status = serializers.SerializerMethodField()
    amount_paid = serializers.SerializerMethodField()
    payment = serializers.SerializerMethodField()

    class Meta:
        model = Application
        fields = [
            'id', 'student', 'course', 'course_detail', 'mode_of_learning',
            'location', 'location_detail', 'created_at',
            'payment_status', 'amount_paid', 'payment',
        ]
        read_only_fields = ['student', 'created_at']

    def _latest_payment(self, obj):
        if not hasattr(obj, '_latest_payment_cache'):
            obj._latest_payment_cache = obj.payments.order_by('-created_at').first()
        return obj._latest_payment_cache

    def get_payment_status(self, obj):
        """Simplified status for the student dashboard."""
        payment = self._latest_payment(obj)
        if not payment:
            return 'not_started'
        if payment.status == payment.Status.PAID:
            return 'paid'
        if payment.status == payment.Status.AWAITING_CONFIRMATION:
            return 'in_review'
        return 'not_started'

    def get_amount_paid(self, obj):
        payment = self._latest_payment(obj)
        if not payment or payment.status != payment.Status.PAID:
            return None
        return str(payment.confirmed_amount or payment.amount)

    def get_payment(self, obj):
        """Full raw payment detail — used by the admin Backstage panel."""
        payment = self._latest_payment(obj)
        if not payment:
            return None
        return {
            "id": str(payment.id),
            "status": payment.status,
            "method": payment.method,
            "payment_type": payment.payment_type,
            "amount": str(payment.amount),
            "confirmed_amount": str(payment.confirmed_amount) if payment.confirmed_amount else None,
            "created_at": payment.created_at.isoformat(),
        }