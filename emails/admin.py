from django.contrib import admin
from .models import EmailVerification, EmailTemplate, SentEmail


@admin.register(EmailTemplate)
class EmailTemplateAdmin(admin.ModelAdmin):
    list_display = ['name', 'template_type', 'subject', 'is_active', 'created_at']
    list_filter = ['template_type', 'is_active', 'created_at']
    search_fields = ['name', 'subject', 'template_type']
    readonly_fields = ['created_at', 'updated_at']
    
    fieldsets = (
        ('Template Info', {
            'fields': ('name', 'template_type', 'is_active')
        }),
        ('Email Content', {
            'fields': ('subject', 'html_content', 'text_content')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )


@admin.register(EmailVerification)
class EmailVerificationAdmin(admin.ModelAdmin):
    list_display = ['user', 'user_email', 'is_verified', 'created_at', 'expires_at']
    list_filter = ['is_verified', 'created_at', 'expires_at']
    search_fields = ['user__email', 'user__name', 'token']
    readonly_fields = ['token', 'created_at', 'verified_at']
    
    def user_email(self, obj):
        return obj.user.email
    user_email.short_description = 'Email'
    
    actions = ['mark_as_verified']
    
    def mark_as_verified(self, request, queryset):
        for verification in queryset:
            if not verification.is_verified:
                verification.verify()
        self.message_user(request, f"Marked {queryset.count()} verifications as verified.")
    mark_as_verified.short_description = "Mark selected as verified"


@admin.register(SentEmail)
class SentEmailAdmin(admin.ModelAdmin):
    list_display = ['recipient_email', 'subject', 'template_type', 'status', 'sent_at', 'created_at']
    list_filter = ['status', 'template_type', 'sent_at', 'created_at']
    search_fields = ['recipient_email', 'recipient_name', 'subject', 'sendgrid_message_id']
    readonly_fields = ['sendgrid_message_id', 'sent_at', 'delivered_at', 'created_at']
    
    fieldsets = (
        ('Email Details', {
            'fields': ('recipient_email', 'recipient_name', 'sender_email', 'subject', 'template_type')
        }),
        ('Status & Tracking', {
            'fields': ('status', 'sendgrid_message_id', 'sent_at', 'delivered_at', 'failed_reason')
        }),
        ('Related Objects', {
            'fields': ('user', 'enrollment'),
            'classes': ('collapse',)
        }),
    )
    
    actions = ['resend_failed_emails']
    
    def resend_failed_emails(self, request, queryset):
        # This would require implementing a resend functionality
        failed_emails = queryset.filter(status='failed')
        self.message_user(request, f"Found {failed_emails.count()} failed emails. Resending functionality can be implemented.")
    resend_failed_emails.short_description = "Resend failed emails"
