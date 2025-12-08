from django.contrib import admin
from .models import Standard, Subject, TuitionBatch, TuitionStudent, TuitionEnrollment, TuitionAttendance, TuitionFee


@admin.register(Standard)
class StandardAdmin(admin.ModelAdmin):
    list_display = ['name', 'code', 'order', 'is_active']
    list_filter = ['is_active']
    search_fields = ['name', 'code']
    ordering = ['order']


@admin.register(Subject)
class SubjectAdmin(admin.ModelAdmin):
    list_display = ['name', 'code', 'is_active']
    list_filter = ['is_active', 'standards']
    search_fields = ['name', 'code']
    filter_horizontal = ['standards']


@admin.register(TuitionBatch)
class TuitionBatchAdmin(admin.ModelAdmin):
    list_display = ['name', 'code', 'standard', 'subject', 'teacher', 'monthly_fee', 'is_active']
    list_filter = ['is_active', 'standard', 'subject']
    search_fields = ['name', 'code']


@admin.register(TuitionStudent)
class TuitionStudentAdmin(admin.ModelAdmin):
    list_display = ['name', 'phone', 'parent_name', 'standard', 'is_active']
    list_filter = ['is_active', 'standard']
    search_fields = ['name', 'phone', 'parent_name', 'email']


@admin.register(TuitionEnrollment)
class TuitionEnrollmentAdmin(admin.ModelAdmin):
    list_display = ['student', 'mode', 'batch', 'subject', 'is_active', 'start_date']
    list_filter = ['is_active', 'mode']
    search_fields = ['student__name']


@admin.register(TuitionAttendance)
class TuitionAttendanceAdmin(admin.ModelAdmin):
    list_display = ['enrollment', 'date', 'status', 'marked_by']
    list_filter = ['status', 'date']
    date_hierarchy = 'date'


@admin.register(TuitionFee)
class TuitionFeeAdmin(admin.ModelAdmin):
    list_display = ['enrollment', 'month', 'year', 'total_amount', 'paid_amount', 'status']
    list_filter = ['status', 'year', 'month']
    search_fields = ['enrollment__student__name']
