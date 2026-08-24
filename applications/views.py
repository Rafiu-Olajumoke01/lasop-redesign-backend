from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated, IsAdminUser
from django.shortcuts import get_object_or_404
from .models import Application
from .serializers import ApplicationSerializer
from users.serializers import UserSerializer
from users.models import User


class ApplicationListCreateView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        if request.user.is_staff:
            applications = Application.objects.all().select_related('student', 'course')
        else:
            applications = Application.objects.filter(student=request.user)
        serializer = ApplicationSerializer(applications, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def post(self, request):
        serializer = ApplicationSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save(student=request.user)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class ApplicationDetailView(APIView):
    """Handles GET (single application), PATCH (staff-only, e.g. assigning cohort),
    and DELETE (staff or owning student) for a single application."""
    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        try:
            if request.user.is_staff:
                application = Application.objects.get(pk=pk)
            else:
                application = Application.objects.get(pk=pk, student=request.user)
        except Application.DoesNotExist:
            return Response({'error': 'Application not found'}, status=status.HTTP_404_NOT_FOUND)

        serializer = ApplicationSerializer(application)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def patch(self, request, pk):
        if not request.user.is_staff:
            return Response({'error': 'Not authorized'}, status=status.HTTP_403_FORBIDDEN)
        try:
            application = Application.objects.get(pk=pk)
        except Application.DoesNotExist:
            return Response({'error': 'Application not found'}, status=status.HTTP_404_NOT_FOUND)

        serializer = ApplicationSerializer(application, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, pk):
        try:
            if request.user.is_staff:
                application = Application.objects.get(pk=pk)
            else:
                application = Application.objects.get(pk=pk, student=request.user)
        except Application.DoesNotExist:
            return Response({'error': 'Application not found'}, status=status.HTTP_404_NOT_FOUND)
        application.delete()
        return Response({'message': 'Course removed successfully'}, status=status.HTTP_204_NO_CONTENT)


class GroupedApplicantsView(APIView):
    """
    Staff-only. Groups Application rows by student so Backstage can render
    one card per applicant with all of their course entries inside it.

    Bucket rule: a student is "an applicant" as long as at least one of
    their Application rows is still missing ANY of the three promotion
    gates:
      1. Cohort assigned
      2. Tutor assigned
      3. Latest payment status == paid

    The moment every course they've applied for satisfies all three gates,
    they no longer appear here — they're a student. If they later apply
    for a new course, a fresh Application row (missing one of the gates)
    brings them back into this list.

    Within an applicant's course list: fully-completed courses (all three
    gates satisfied) come first since they need no review, courses still
    missing a gate come last.

    Applicant ordering: oldest applicant first (first-come-first-served),
    anchored to the EARLIEST created_at across all of a student's
    Application rows.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        if not request.user.is_staff:
            return Response({'error': 'Not authorized'}, status=status.HTTP_403_FORBIDDEN)

        applications = Application.objects.select_related(
            'student', 'course', 'cohort', 'cohort__tutor', 'location'
        ).prefetch_related('payments')

        groups = {}
        for app in applications:
            groups.setdefault(app.student_id, []).append(app)

        def is_pending(a):
            """An Application still needs review if cohort, tutor, or a
            confirmed 'paid' payment is missing."""
            latest_payment = a.payments.order_by('-created_at').first()
            payment_paid = (
                latest_payment is not None
                and latest_payment.status == latest_payment.Status.PAID
            )
            return a.cohort_id is None or a.tutor_id is None or not payment_paid

        applicant_groups = []
        for apps in groups.values():
            still_applicant = any(is_pending(a) for a in apps)
            if not still_applicant:
                continue

            completed = sorted((a for a in apps if not is_pending(a)), key=lambda a: a.created_at)
            pending = sorted((a for a in apps if is_pending(a)), key=lambda a: a.created_at)

            applicant_groups.append({
                'student': apps[0].student,
                'anchor': min(a.created_at for a in apps),
                'courses': completed + pending,
            })

        applicant_groups.sort(key=lambda g: g['anchor'])

        data = [
            {
                'student': UserSerializer(g['student']).data,
                'courses': ApplicationSerializer(g['courses'], many=True).data,
            }
            for g in applicant_groups
        ]

        return Response(data, status=status.HTTP_200_OK)


class StudentApplicationsView(APIView):
    """Admin-only: list all courses (Applications) a given student is enrolled in.
    Used on the student detail page in Backstage to render the 'Courses' rows."""
    permission_classes = [IsAdminUser]

    def get(self, request, user_id):
        student = get_object_or_404(User, id=user_id, is_tutor=False, is_staff=False)

        applications = Application.objects.filter(student=student).select_related(
            'course', 'cohort', 'tutor__user'
        )

        data = []
        for app in applications:
            tutor_name = None
            if app.tutor and app.tutor.user:
                tutor_name = app.tutor.user.get_full_name() or app.tutor.user.email

            data.append({
                'application_id': app.id,
                'course_id': app.course_id,
                'course_name': app.course.title if app.course else None,
                'cohort_id': app.cohort_id,
                'cohort_name': app.cohort.name if app.cohort else None,
                'tutor_id': app.tutor_id,
                'tutor_name': tutor_name,
                'status': app.status,
                'mode_of_learning': app.mode_of_learning,
            })

        return Response(data, status=status.HTTP_200_OK)