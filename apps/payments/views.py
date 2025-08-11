from django.shortcuts import render
from django.db import transaction
from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView
from drf_spectacular.utils import extend_schema, OpenApiParameter
from drf_spectacular.types import OpenApiTypes
from datetime import date, datetime
from decimal import Decimal

from apps.courses.models import Course
from .models import Enrollment, Payment, TaxInvoice, InstallmentPlan
from .serializers import CourseEnrollmentSerializer, PaymentSerializer, CoursePreviewSerializer, EnrollmentSerializer, InstallmentPlanSerializer


class CourseEnrollmentView(APIView):
    """
    Student course enrollment API - handles course purchase with automatic enrollment and payment creation
    """
    permission_classes = [permissions.IsAuthenticated]
    
    @extend_schema(
        summary="Purchase Course and Auto-Enroll",
        description="Student purchases a course which automatically creates enrollment and payment record",
        request=CourseEnrollmentSerializer,
        responses={
            201: {
                "type": "object", 
                "properties": {
                    "message": {"type": "string"},
                    "enrollment_id": {"type": "integer"},
                    "payment_id": {"type": "integer"},
                    "total_amount": {"type": "number"},
                    "payment_status": {"type": "string"}
                }
            },
            400: {"type": "object", "properties": {"error": {"type": "string"}}},
            404: {"type": "object", "properties": {"error": {"type": "string"}}}
        }
    )
    def post(self, request):
        """Handle course purchase and enrollment"""
        
        # Validate request data
        serializer = CourseEnrollmentSerializer(data=request.data)
        if not serializer.is_valid():
            return Response({"error": serializer.errors}, status=status.HTTP_400_BAD_REQUEST)
        
        course_id = serializer.validated_data['course_id']
        payment_method = serializer.validated_data['payment_method']
        transaction_id = serializer.validated_data.get('transaction_id')
        payment_gateway_response = serializer.validated_data.get('payment_gateway_response', {})
        
        try:
            # Get course
            course = Course.objects.get(id=course_id)
            
            # Check if course allows public enrollment
            if not course.allow_public_enrollment:
                return Response({
                    "error": "This course is not available for public enrollment. Contact admin for access."
                }, status=status.HTTP_403_FORBIDDEN)
            
            # Check if user already enrolled
            existing_enrollment = Enrollment.objects.filter(
                user=request.user, 
                course=course, 
                active=True
            ).first()
            
            if existing_enrollment:
                return Response({
                    "error": "You are already enrolled in this course"
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # Calculate amounts (18% GST)
            course_price = course.price or Decimal('0.00')
            tax_rate = Decimal('0.18')  # 18% GST
            tax_amount = course_price * tax_rate
            total_amount = course_price + tax_amount
            
            # Start database transaction
            with transaction.atomic():
                
                # 1. Create Enrollment
                enrollment = Enrollment.objects.create(
                    user=request.user,
                    course=course,
                    enrollment_type='individual',
                    total_amount=total_amount,
                    tax_amount=tax_amount,
                    payment_status='completed' if course.is_free else 'completed',  # Completed since payment came from app
                    has_installment_plan=False,
                    active=True
                )
                
                # 2. Create Payment Record
                payment = Payment.objects.create(
                    enrollment=enrollment,
                    installment_number=1,  # Single payment
                    amount=course_price,
                    tax_amount=tax_amount,
                    payment_method=payment_method,
                    transaction_id=transaction_id,
                    payment_date=datetime.now(),
                    due_date=date.today(),
                    status='completed',  # Payment already processed by app
                    notes=f"Auto-generated from app purchase. Gateway Response: {payment_gateway_response}"
                )
                
                # 3. Create Tax Invoice (if needed)
                if not course.is_free and total_amount > 0:
                    invoice_number = f"INV-{enrollment.id}-{payment.id}-{datetime.now().strftime('%Y%m%d')}"
                    TaxInvoice.objects.create(
                        enrollment=enrollment,
                        payment=payment,
                        invoice_number=invoice_number,
                        subtotal=course_price,
                        tax_rate=tax_rate * 100,  # Store as percentage
                        tax_amount=tax_amount,
                        total_amount=total_amount
                    )
                
                return Response({
                    "message": "Course purchased and enrollment created successfully",
                    "enrollment_id": enrollment.id,
                    "payment_id": payment.id,
                    "total_amount": float(total_amount),
                    "payment_status": enrollment.payment_status,
                    "course_title": course.title
                }, status=status.HTTP_201_CREATED)
                
        except Course.DoesNotExist:
            return Response({
                "error": "Course not found"
            }, status=status.HTTP_404_NOT_FOUND)
            
        except Exception as e:
            return Response({
                "error": f"Failed to process enrollment: {str(e)}"
            }, status=status.HTTP_400_BAD_REQUEST)


class UserEnrollmentsView(generics.ListAPIView):
    """
    Get all enrollments for the authenticated user with payment and installment details
    """
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = EnrollmentSerializer
    
    def get_queryset(self):
        return Enrollment.objects.filter(
            user=self.request.user,
            active=True
        ).select_related('course', 'user').prefetch_related('payments', 'installment_plan_details')
    
    @extend_schema(
        summary="Get User's Course Enrollments",
        description="Retrieve all active course enrollments with payment and installment plan details",
        responses={200: EnrollmentSerializer(many=True)}
    )
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)


class EnrollmentPaymentHistoryView(APIView):
    """
    Get payment history for a specific enrollment
    """
    permission_classes = [permissions.IsAuthenticated]
    
    @extend_schema(
        summary="Get Enrollment Payment History", 
        description="Get all payment records for a specific enrollment",
        parameters=[
            OpenApiParameter(
                name='enrollment_id',
                type=OpenApiTypes.INT,
                location=OpenApiParameter.PATH,
                description='Enrollment ID'
            )
        ],
        responses={200: PaymentSerializer(many=True)}
    )
    def get(self, request, enrollment_id):
        try:
            # Verify enrollment belongs to user
            enrollment = Enrollment.objects.get(
                id=enrollment_id,
                user=request.user,
                active=True
            )
            
            payments = Payment.objects.filter(enrollment=enrollment).order_by('-payment_date')
            serializer = PaymentSerializer(payments, many=True)
            
            return Response({
                "enrollment": {
                    "id": enrollment.id,
                    "course_title": enrollment.course.title,
                    "total_amount": enrollment.total_amount,
                    "payment_status": enrollment.payment_status,
                    "outstanding_amount": enrollment.outstanding_amount
                },
                "payments": serializer.data
            }, status=status.HTTP_200_OK)
            
        except Enrollment.DoesNotExist:
            return Response({
                "error": "Enrollment not found or does not belong to you"
            }, status=status.HTTP_404_NOT_FOUND)


class EnrollmentInstallmentPlanView(APIView):
    """
    Get detailed installment plan information for a specific enrollment
    """
    permission_classes = [permissions.IsAuthenticated]
    
    @extend_schema(
        summary="Get Enrollment Installment Plan Details",
        description="Get detailed installment plan information for a specific enrollment (admin-created enrollments only)",
        parameters=[
            OpenApiParameter(
                name='enrollment_id',
                type=OpenApiTypes.INT,
                location=OpenApiParameter.PATH,
                description='Enrollment ID'
            )
        ],
        responses={
            200: InstallmentPlanSerializer,
            404: {"type": "object", "properties": {"error": {"type": "string"}}}
        }
    )
    def get(self, request, enrollment_id):
        try:
            # Verify enrollment belongs to user
            enrollment = Enrollment.objects.get(
                id=enrollment_id,
                user=request.user,
                active=True
            )
            
            # Check if enrollment has installment plan
            if not enrollment.has_installment_plan:
                return Response({
                    "error": "This enrollment does not have an installment plan"
                }, status=status.HTTP_404_NOT_FOUND)
            
            try:
                installment_plan = InstallmentPlan.objects.get(enrollment=enrollment)
                serializer = InstallmentPlanSerializer(installment_plan)
                
                # Get additional payment information
                payments = Payment.objects.filter(enrollment=enrollment).order_by('installment_number')
                payment_serializer = PaymentSerializer(payments, many=True)
                
                return Response({
                    "installment_plan": serializer.data,
                    "payments": payment_serializer.data,
                    "enrollment_summary": {
                        "id": enrollment.id,
                        "course_title": enrollment.course.title,
                        "total_amount": enrollment.total_amount,
                        "paid_amount": enrollment.paid_amount,
                        "outstanding_amount": enrollment.outstanding_amount,
                        "payment_status": enrollment.payment_status
                    }
                }, status=status.HTTP_200_OK)
                
            except InstallmentPlan.DoesNotExist:
                return Response({
                    "error": "Installment plan not found for this enrollment"
                }, status=status.HTTP_404_NOT_FOUND)
            
        except Enrollment.DoesNotExist:
            return Response({
                "error": "Enrollment not found or does not belong to you"
            }, status=status.HTTP_404_NOT_FOUND)


class CoursePricingPreviewView(APIView):
    """
    Get course pricing breakdown before purchase
    """
    permission_classes = [permissions.IsAuthenticated]
    
    @extend_schema(
        summary="Get Course Pricing Breakdown",
        description="Get detailed pricing information for a course before purchase",
        parameters=[
            OpenApiParameter(
                name='course_id',
                type=OpenApiTypes.INT,
                location=OpenApiParameter.PATH,
                description='Course ID'
            )
        ],
        responses={200: CoursePreviewSerializer}
    )
    def get(self, request, course_id):
        try:
            course = Course.objects.get(id=course_id)
            
            # Check if user already enrolled
            is_enrolled = Enrollment.objects.filter(
                user=request.user,
                course=course,
                active=True
            ).exists()
            
            serializer = CoursePreviewSerializer(course)
            
            return Response({
                "course_pricing": serializer.data,
                "is_enrolled": is_enrolled,
                "can_purchase": not is_enrolled and course.allow_public_enrollment,
                "allow_public_enrollment": course.allow_public_enrollment
            }, status=status.HTTP_200_OK)
            
        except Course.DoesNotExist:
            return Response({
                "error": "Course not found"
            }, status=status.HTTP_404_NOT_FOUND)
