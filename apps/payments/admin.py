from django.contrib import admin
from django.utils.html import format_html
from django.http import JsonResponse
from django.urls import path
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
    
    def get_form(self, request, obj=None, **kwargs):
        form = super().get_form(request, obj, **kwargs)
        if obj and obj.course and obj.course.is_free_course:
            # Make payment fields optional for free courses
            form.base_fields['total_amount'].required = False
            form.base_fields['tax_amount'].required = False
        return form
    
    def save_model(self, request, obj, form, change):
        # Auto-populate payment details based on course
        if obj.course:
            if obj.course.is_free_course:
                obj.total_amount = 0
                obj.tax_amount = 0
                obj.payment_status = 'free'
            elif not obj.total_amount or obj.total_amount == 0:
                obj.total_amount = obj.course.total_price
                obj.tax_amount = obj.course.tax_amount
        super().save_model(request, obj, form, change)
    
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
            'fields': ('total_amount', 'tax_amount', 'payment_status', 'paid_amount', 'outstanding_amount'),
            'description': 'Payment fields are auto-populated based on course pricing. For free courses, these will be set to 0.'
        }),
        ('Installment Plan', {
            'fields': ('has_installment_plan',),
            'description': 'Check this to create an installment plan after saving the enrollment'
        }),
        ('Status', {
            'fields': ('active',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        })
    )
    
    class Media:
        js = ('admin/js/enrollment_admin.js',)
    
    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path('get-course-pricing/', self.get_course_pricing, name='get_course_pricing'),
        ]
        return custom_urls + urls
    
    def get_course_pricing(self, request):
        from apps.courses.models import Course
        course_id = request.GET.get('course_id')
        if course_id:
            try:
                course = Course.objects.get(id=course_id)
                return JsonResponse({
                    'is_free': course.is_free_course,
                    'total_price': float(course.total_price),
                    'tax_amount': float(course.tax_amount),
                    'base_price': float(course.price or 0)
                })
            except Course.DoesNotExist:
                pass
        return JsonResponse({'error': 'Course not found'}, status=404)

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
    
    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == "enrollment":
            # Only show enrollments that are paid and don't have installment plans yet
            kwargs["queryset"] = Enrollment.objects.filter(
                payment_status__in=['pending', 'partial'],
                has_installment_plan=True,
                installment_plan_details__isnull=True
            ).select_related('user', 'course')
        return super().formfield_for_foreignkey(db_field, request, **kwargs)
    
    fieldsets = (
        ('Enrollment', {
            'fields': ('enrollment',),
            'description': 'Select an enrollment that has installment plan enabled but no plan created yet.'
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
