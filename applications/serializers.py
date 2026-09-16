from rest_framework import serializers
from .models import Application
from courses.models import Course, Location
from cohorts.serializers import CohortSerializer
from tutors.serializers import TutorSerializer
from users.serializers import UserSerializer


class LocationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Location
        fields = ['id', 'name', 'address']


class CourseSerializer(serializers.ModelSerializer):
    class Meta:
        model = Course
        fields = ['id', 'title', 'category', 'duration', 'fee']


class ApplicationSerializer(serializers.ModelSerializer):
    student_detail = UserSerializer(source='student', read_only=True)
    course_detail = CourseSerializer(source='course', read_only=True)
    location_detail = LocationSerializer(source='location', read_only=True)
    cohort_detail = CohortSerializer(source='cohort', read_only=True)
    tutor_detail = TutorSerializer(source='tutor', read_only=True)
    payment_status = serializers.SerializerMethodField()
    amount_paid = serializers.SerializerMethodField()
    payment = serializers.SerializerMethodField()

    class Meta:
        model = Application
        fields = [
            'id', 'student', 'student_detail', 'course', 'course_detail', 'mode_of_learning',
            'location', 'location_detail', 'cohort', 'cohort_detail', 'tutor', 'tutor_detail',
            'created_at', 'payment_status', 'amount_paid', 'payment',
        ]
        read_only_fields = ['student', 'created_at']

    def _latest_payment(self, obj):
        if not hasattr(obj, '_latest_payment_cache'):
            obj._latest_payment_cache = obj.payments.order_by('-created_at').first()
        return obj._latest_payment_cache

    def get_payment_status(self, obj):
        amount_paid = self.get_amount_paid(obj)
        amount_paid = float(amount_paid) if amount_paid else 0
        fee = float(obj.course.fee)

        if fee > 0 and amount_paid >= fee:
            return 'paid'

        payment = self._latest_payment(obj)
        if payment and payment.status == payment.Status.AWAITING_CONFIRMATION:
            return 'in_review'

        if amount_paid > 0:
            return 'partially_paid'

        return 'not_started'

    def get_amount_paid(self, obj):
        from django.db.models import Sum, F
        from .models import Payment as PaymentModel
        total = obj.payments.filter(status=PaymentModel.Status.PAID).aggregate(
            total=Sum(F('confirmed_amount'))
        )['total']
        if total is None:
            # fall back to `amount` for any paid rows that never got a confirmed_amount set
            total = obj.payments.filter(status=PaymentModel.Status.PAID).aggregate(
                total=Sum(F('amount'))
            )['total']
        return str(total) if total else None

    def get_payment(self, obj):
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
            "promo_code": payment.promo_code.code if payment.promo_code else None,
        }