from rest_framework import serializers
from decimal import Decimal
from .models import Enrollment, Payment, InstallmentPlan, TaxInvoice
from apps.courses.models import Course


class CourseEnrollmentSerializer(serializers.Serializer):
    """
    Serializer for course purchase/enrollment from mobile app
    """
    course_id = serializers.IntegerField(required=True)
    payment_method = serializers.ChoiceField(
        choices=[
            ('razorpay', 'Razorpay'),
            ('stripe', 'Stripe'),
            ('paytm', 'Paytm'),
            ('phonepe', 'PhonePe'),
            ('gpay', 'Google Pay'),
            ('other', 'Other')
        ],
        required=True
    )
    transaction_id = serializers.CharField(
        max_length=100, 
        required=False,
        help_text="Payment gateway transaction ID"
    )
    payment_gateway_response = serializers.JSONField(
        required=False,
        help_text="Complete payment gateway response data"
    )
    
    def validate_course_id(self, value):
        """Validate that course exists and is purchasable"""
        try:
            course = Course.objects.get(id=value)
            if not course.price or course.price <= 0:
                if not course.is_free:
                    raise serializers.ValidationError("Course price is not set")
            return value
        except Course.DoesNotExist:
            raise serializers.ValidationError("Course does not exist")


class PaymentSerializer(serializers.ModelSerializer):
    """
    Serializer for Payment model
    """
    enrollment_course = serializers.CharField(source='enrollment.course.title', read_only=True)
    enrollment_user = serializers.CharField(source='enrollment.user.name', read_only=True)
    
    class Meta:
        model = Payment
        fields = [
            'id', 'enrollment', 'enrollment_course', 'enrollment_user',
            'installment_number', 'amount', 'tax_amount', 'payment_method',
            'transaction_id', 'payment_date', 'due_date', 'status',
            'invoice_number', 'notes', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class EnrollmentSerializer(serializers.ModelSerializer):
    """
    Serializer for Enrollment model
    """
    course_title = serializers.CharField(source='course.title', read_only=True)
    course_price = serializers.DecimalField(source='course.price', max_digits=10, decimal_places=2, read_only=True)
    course_total_price = serializers.DecimalField(source='course.total_price', max_digits=10, decimal_places=2, read_only=True)
    user_name = serializers.CharField(source='user.name', read_only=True)
    user_email = serializers.CharField(source='user.email', read_only=True)
    payments = PaymentSerializer(many=True, read_only=True)
    installment_plan = serializers.SerializerMethodField()
    paid_amount = serializers.ReadOnlyField()
    outstanding_amount = serializers.ReadOnlyField()
    payment_progress = serializers.SerializerMethodField()
    
    class Meta:
        model = Enrollment
        fields = [
            'id', 'user', 'user_name', 'user_email', 'course', 'course_title', 
            'course_price', 'course_total_price', 'team', 'enrollment_type', 
            'enrolled_on', 'total_amount', 'tax_amount', 'payment_status', 
            'has_installment_plan', 'installment_plan', 'active', 'paid_amount',
            'outstanding_amount', 'payment_progress', 'payments', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'enrolled_on', 'created_at', 'updated_at']
    
    def get_installment_plan(self, obj):
        """Get installment plan details if exists"""
        try:
            plan = obj.installment_plan_details
            if plan:
                return {
                    'id': plan.id,
                    'total_installments': plan.total_installments,
                    'installment_amount': plan.installment_amount,
                    'frequency': plan.frequency,
                    'start_date': plan.start_date,
                    'remaining_installments': plan.total_installments - obj.payments.filter(status='completed').count(),
                    'next_due_date': self.get_next_due_date(obj, plan)
                }
        except:
            pass
        return None
    
    def get_next_due_date(self, enrollment, plan):
        """Calculate next payment due date"""
        from datetime import datetime, timedelta
        
        completed_payments = enrollment.payments.filter(status='completed').count()
        if completed_payments >= plan.total_installments:
            return None
        
        # Calculate next due date based on frequency (simplified to avoid extra dependencies)
        if plan.frequency == 'monthly':
            # Add months by adding 30 days per month (approximation)
            days_to_add = completed_payments * 30
            next_date = plan.start_date + timedelta(days=days_to_add)
        else:
            # For custom frequency, assume monthly
            days_to_add = completed_payments * 30
            next_date = plan.start_date + timedelta(days=days_to_add)
        
        return next_date
    
    def get_payment_progress(self, obj):
        """Get payment progress percentage"""
        if obj.total_amount and obj.total_amount > 0:
            progress = (obj.paid_amount / obj.total_amount) * 100
            return round(float(progress), 2)
        return 100.0 if obj.payment_status == 'free' else 0.0


class InstallmentPlanSerializer(serializers.ModelSerializer):
    """
    Serializer for Installment Plan model
    """
    enrollment_details = EnrollmentSerializer(source='enrollment', read_only=True)
    
    class Meta:
        model = InstallmentPlan
        fields = [
            'id', 'enrollment', 'enrollment_details', 'total_installments',
            'installment_amount', 'frequency', 'start_date', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class TaxInvoiceSerializer(serializers.ModelSerializer):
    """
    Serializer for Tax Invoice model
    """
    enrollment_details = serializers.CharField(source='enrollment.user.name', read_only=True)
    course_title = serializers.CharField(source='enrollment.course.title', read_only=True)
    
    class Meta:
        model = TaxInvoice
        fields = [
            'id', 'enrollment', 'enrollment_details', 'course_title', 'payment',
            'invoice_number', 'invoice_date', 'subtotal', 'tax_rate', 'tax_amount',
            'total_amount', 'invoice_pdf_path', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'invoice_date', 'created_at', 'updated_at']


class CoursePreviewSerializer(serializers.ModelSerializer):
    """
    Serializer for course purchase preview - shows pricing breakdown
    """
    base_price = serializers.DecimalField(source='price', max_digits=10, decimal_places=2, read_only=True)
    tax_rate = serializers.SerializerMethodField()
    tax_amount = serializers.SerializerMethodField() 
    total_amount = serializers.SerializerMethodField()
    is_free = serializers.BooleanField(read_only=True)
    
    class Meta:
        model = Course
        fields = ['id', 'title', 'base_price', 'tax_rate', 'tax_amount', 'total_amount', 'is_free', 'allow_public_enrollment']
    
    def get_tax_rate(self, obj):
        """Return tax rate as percentage"""
        return 18.0  # 18% GST
    
    def get_tax_amount(self, obj):
        """Calculate tax amount"""
        if obj.is_free or not obj.price:
            return Decimal('0.00')
        return obj.price * Decimal('0.18')
    
    def get_total_amount(self, obj):
        """Calculate total amount including tax"""
        if obj.is_free or not obj.price:
            return Decimal('0.00')
        return obj.price + (obj.price * Decimal('0.18'))