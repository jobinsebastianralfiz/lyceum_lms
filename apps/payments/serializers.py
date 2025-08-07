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
    user_name = serializers.CharField(source='user.name', read_only=True)
    payments = PaymentSerializer(many=True, read_only=True)
    paid_amount = serializers.ReadOnlyField()
    outstanding_amount = serializers.ReadOnlyField()
    
    class Meta:
        model = Enrollment
        fields = [
            'id', 'user', 'user_name', 'course', 'course_title', 'course_price',
            'team', 'enrollment_type', 'enrolled_on', 'total_amount', 'tax_amount',
            'payment_status', 'has_installment_plan', 'active', 'paid_amount',
            'outstanding_amount', 'payments', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'enrolled_on', 'created_at', 'updated_at']


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
        fields = ['id', 'title', 'base_price', 'tax_rate', 'tax_amount', 'total_amount', 'is_free']
    
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