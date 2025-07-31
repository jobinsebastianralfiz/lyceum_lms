from django.contrib import admin
from django.utils.html import format_html
from .models import Enrollment, InstallmentPlan, Payment, TaxInvoice

class PaymentInline(admin.TabularInline):
    model = Payment
    extra = 0
    readonly_fields = ('transaction_id', 'payment_date', 'created_at')

class InstallmentPlanInline(admin.StackedInline):
    model = InstallmentPlan
    extra = 0
    fields = ('total_installments', 'installment_amount', 'frequency', 'start_date')
    can_delete = True

@admin.register(Enrollment)
class EnrollmentAdmin(admin.ModelAdmin):
    list_display = ('enrollment_display_admin', 'course', 'enrollment_type', 'payment_status', 'total_amount', 'outstanding_amount_display', 'enrolled_on')
    list_filter = ('enrollment_type', 'payment_status', 'active', 'enrolled_on')
    search_fields = ('user__name', 'user__email', 'course__title', 'team__name')
    readonly_fields = ('paid_amount', 'outstanding_amount', 'enrolled_on', 'created_at', 'updated_at')
    inlines = [InstallmentPlanInline, PaymentInline]
    
    def enrollment_display_admin(self, obj):
        if obj.enrollment_type == 'team' and obj.team:
            return format_html('<i class="fas fa-users" style="color: #667eea;"></i> {}', obj.team.name)
        return obj.user.name
    enrollment_display_admin.short_description = 'Student/Team'
    
    def outstanding_amount_display(self, obj):
        try:
            amount = obj.outstanding_amount
            if amount > 0:
                return format_html('<span style="color: red;">₹{:.2f}</span>', amount)
            return format_html('<span style="color: green;">₹0.00</span>')
        except (TypeError, AttributeError):
            return format_html('<span style="color: gray;">N/A</span>')
    outstanding_amount_display.short_description = 'Outstanding'
    
    fieldsets = (
        ('Enrollment Details', {
            'fields': ('user', 'course', 'team', 'enrollment_type', 'enrolled_on')
        }),
        ('Payment Information', {
            'fields': ('total_amount', 'tax_amount', 'payment_status', 'paid_amount', 'outstanding_amount')
        }),
        ('Installment Plan', {
            'fields': ('has_installment_plan',)
        }),
        ('Status', {
            'fields': ('active',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        })
    )

@admin.register(InstallmentPlan)
class InstallmentPlanAdmin(admin.ModelAdmin):
    list_display = ('enrollment_display', 'total_installments', 'installment_amount', 'frequency', 'start_date')
    list_filter = ('frequency', 'start_date')
    search_fields = ('enrollment__user__name', 'enrollment__course__title')
    readonly_fields = ('created_at', 'updated_at')
    
    def enrollment_display(self, obj):
        if obj.enrollment:
            return f"{obj.enrollment.user.name} - {obj.enrollment.course.title}"
        return "No enrollment linked"
    enrollment_display.short_description = 'Enrollment'
    
    fieldsets = (
        ('Enrollment', {
            'fields': ('enrollment',)
        }),
        ('Plan Details', {
            'fields': ('total_installments', 'installment_amount', 'frequency', 'start_date')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        })
    )

@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ('enrollment_user', 'enrollment_course', 'installment_number', 'amount', 'status', 'payment_method', 'due_date', 'payment_date')
    list_filter = ('status', 'payment_method', 'due_date', 'payment_date')
    search_fields = ('enrollment__user__name', 'enrollment__course__title', 'transaction_id', 'invoice_number')
    readonly_fields = ('created_at', 'updated_at')
    
    def enrollment_user(self, obj):
        return obj.enrollment.user.name
    enrollment_user.short_description = 'Student'
    
    def enrollment_course(self, obj):
        return obj.enrollment.course.title
    enrollment_course.short_description = 'Course'
    
    fieldsets = (
        ('Payment Details', {
            'fields': ('enrollment', 'installment_number', 'amount', 'tax_amount')
        }),
        ('Payment Information', {
            'fields': ('payment_method', 'transaction_id', 'payment_date', 'due_date')
        }),
        ('Status & Invoice', {
            'fields': ('status', 'invoice_number', 'notes')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        })
    )

@admin.register(TaxInvoice)
class TaxInvoiceAdmin(admin.ModelAdmin):
    list_display = ('invoice_number', 'enrollment_user', 'enrollment_course', 'total_amount', 'invoice_date')
    list_filter = ('invoice_date',)
    search_fields = ('invoice_number', 'enrollment__user__name', 'enrollment__course__title')
    readonly_fields = ('invoice_date', 'created_at', 'updated_at')
    
    def enrollment_user(self, obj):
        return obj.enrollment.user.name
    enrollment_user.short_description = 'Student'
    
    def enrollment_course(self, obj):
        return obj.enrollment.course.title
    enrollment_course.short_description = 'Course'
