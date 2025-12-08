from django.contrib import admin
from .models import FeatureConfig


@admin.register(FeatureConfig)
class FeatureConfigAdmin(admin.ModelAdmin):
    list_display = ['__str__', 'updated_at', 'updated_by']

    fieldsets = (
        ('Online Learning', {
            'fields': ('enable_online_courses', 'enable_live_sessions'),
            'description': 'Control online course-related features'
        }),
        ('Students & Enrollment', {
            'fields': ('enable_online_enrollment', 'enable_certificates'),
            'description': 'Control student enrollment and certification features'
        }),
        ('Tuition Management', {
            'fields': ('enable_tuition_management',),
            'description': 'Control offline tuition management features'
        }),
        ('Finance & Payments', {
            'fields': ('enable_finance_management', 'enable_payments'),
            'description': 'Control financial tracking and payment features'
        }),
        ('Assessments & Feedback', {
            'fields': ('enable_assessments',),
            'description': 'Control assignment submissions, quizzes, and reviews'
        }),
        ('Communications', {
            'fields': ('enable_notifications',),
            'description': 'Control notifications and email templates'
        }),
        ('Website Content', {
            'fields': ('enable_website_content',),
            'description': 'Control news, events, testimonials, and landing page content'
        }),
        ('Integrations', {
            'fields': ('enable_youtube_integration',),
            'description': 'Control third-party integrations'
        }),
        ('Analytics', {
            'fields': ('enable_analytics',),
            'description': 'Control analytics and mentor dashboard'
        }),
    )

    def has_add_permission(self, request):
        # Only allow one instance
        return not FeatureConfig.objects.exists()

    def has_delete_permission(self, request, obj=None):
        return False

    def save_model(self, request, obj, form, change):
        obj.updated_by = request.user
        super().save_model(request, obj, form, change)
