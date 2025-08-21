from django.db import models
from django.conf import settings
from apps.courses.models import Course

class Enrollment(models.Model):
    ENROLLMENT_TYPE_CHOICES = [
        ('individual', 'Individual'),
        ('team', 'Team'),
        ('admin_assigned', 'Admin Assigned'),
    ]
    
    PAYMENT_STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('partial', 'Partial'),
        ('completed', 'Completed'),
        ('free', 'Free Course'),
    ]
    
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='enrollments', help_text="Primary student (for individual) or team representative")
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name='enrollments')
    team = models.ForeignKey('users.Team', on_delete=models.CASCADE, related_name='enrollments', null=True, blank=True, help_text="Team for team enrollments")
    enrollment_type = models.CharField(max_length=15, choices=ENROLLMENT_TYPE_CHOICES, default='individual')
    enrolled_on = models.DateTimeField(auto_now_add=True)
    total_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0, blank=True, help_text="Total amount including tax")
    tax_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0, blank=True)
    payment_status = models.CharField(max_length=10, choices=PAYMENT_STATUS_CHOICES, default='pending')
    has_installment_plan = models.BooleanField(default=False, help_text="Whether this enrollment has an installment plan")
    active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def save(self, *args, **kwargs):
        # Auto-set payment details for free courses
        if self.course and self.course.is_free_course:
            self.total_amount = 0
            self.tax_amount = 0
            self.payment_status = 'free'
        elif self.course and not self.total_amount:
            # Auto-populate pricing for paid courses if not set
            self.total_amount = self.course.total_price
            self.tax_amount = self.course.tax_amount
        super().save(*args, **kwargs)
    
    def __str__(self):
        if self.enrollment_type == 'team' and self.team:
            return f"Team: {self.team.name} - {self.course.title}"
        return f"{self.user.name} - {self.course.title}"
    
    @property
    def paid_amount(self):
        payments = self.payments.filter(status='completed')
        return sum(payment.amount or 0 for payment in payments)
    
    @property
    def outstanding_amount(self):
        total = self.total_amount or 0
        paid = self.paid_amount
        return max(0, total - paid)
    
    @property
    def installment_plan(self):
        """Get the installment plan for this enrollment if it exists"""
        try:
            return self.installment_plan_details
        except AttributeError:
            return None
    
    @property
    def enrolled_students(self):
        """Get all students who have access to this enrollment"""
        if self.enrollment_type == 'team' and self.team:
            return self.team.memberships.filter(is_active=True).values_list('user', flat=True)
        return [self.user.id]
    
    @property
    def enrollment_display(self):
        """Display string for enrollment"""
        if self.enrollment_type == 'team' and self.team:
            return f"Team: {self.team.name} ({self.team.member_count} members)"
        return f"Individual: {self.user.name}"
    
    class Meta:
        db_table = 'enrollments'
        unique_together = ['user', 'course']

class InstallmentPlan(models.Model):
    FREQUENCY_CHOICES = [
        ('monthly', 'Monthly'),
        ('custom', 'Custom'),
    ]
    
    enrollment = models.OneToOneField(Enrollment, on_delete=models.CASCADE, related_name='installment_plan_details', null=True, blank=True)
    total_installments = models.PositiveIntegerField()
    installment_amount = models.DecimalField(max_digits=10, decimal_places=2)
    frequency = models.CharField(max_length=10, choices=FREQUENCY_CHOICES, default='monthly')
    start_date = models.DateField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        if hasattr(self, 'enrollment') and self.enrollment:
            return f"Plan for {self.enrollment.user.name} - {self.total_installments} installments"
        return f"Installment Plan - {self.total_installments} installments"
    
    class Meta:
        db_table = 'installment_plans'

class Payment(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('completed', 'Completed'),
        ('overdue', 'Overdue'),
        ('failed', 'Failed'),
    ]
    
    PAYMENT_METHOD_CHOICES = [
        ('razorpay', 'Razorpay'),
        ('cash', 'Cash'),
        ('bank_transfer', 'Bank Transfer'),
        ('other', 'Other'),
    ]
    
    enrollment = models.ForeignKey(Enrollment, on_delete=models.CASCADE, related_name='payments')
    installment_number = models.PositiveIntegerField(default=1)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    tax_amount = models.DecimalField(max_digits=10, decimal_places=2)
    payment_method = models.CharField(max_length=15, choices=PAYMENT_METHOD_CHOICES)
    transaction_id = models.CharField(max_length=100, blank=True, null=True)
    payment_date = models.DateTimeField(null=True, blank=True)
    due_date = models.DateField()
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='pending')
    invoice_number = models.CharField(max_length=50, blank=True, null=True)
    notes = models.TextField(blank=True, null=True)
    
    # Razorpay specific fields
    razorpay_order_id = models.CharField(max_length=100, blank=True, null=True)
    razorpay_payment_id = models.CharField(max_length=100, blank=True, null=True)
    razorpay_signature = models.CharField(max_length=255, blank=True, null=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"Payment {self.installment_number} - {self.enrollment.user.name}"
    
    class Meta:
        db_table = 'payments'
        unique_together = ['enrollment', 'installment_number']

class TaxInvoice(models.Model):
    enrollment = models.ForeignKey(Enrollment, on_delete=models.CASCADE, related_name='tax_invoices')
    payment = models.ForeignKey(Payment, on_delete=models.CASCADE, related_name='tax_invoice', null=True, blank=True)
    invoice_number = models.CharField(max_length=50, unique=True)
    invoice_date = models.DateField(auto_now_add=True)
    subtotal = models.DecimalField(max_digits=10, decimal_places=2)
    tax_rate = models.DecimalField(max_digits=5, decimal_places=2)
    tax_amount = models.DecimalField(max_digits=10, decimal_places=2)
    total_amount = models.DecimalField(max_digits=10, decimal_places=2)
    invoice_pdf_path = models.FileField(upload_to='invoices/', blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"Invoice {self.invoice_number} - {self.enrollment.user.name}"
    
    class Meta:
        db_table = 'tax_invoices'
