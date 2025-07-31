from django.contrib import admin
from .models import Notification, EmailTemplate

@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ('user', 'notification_type', 'title', 'email_sent', 'email_status', 'read', 'created_at')
    list_filter = ('notification_type', 'email_sent', 'email_status', 'read', 'created_at')
    search_fields = ('user__name', 'user__email', 'title', 'message')
    readonly_fields = ('created_at', 'updated_at', 'read_at')
    
    fieldsets = (
        ('Notification Details', {
            'fields': ('user', 'notification_type', 'title', 'message')
        }),
        ('Email Status', {
            'fields': ('email_sent', 'email_status')
        }),
        ('Read Status', {
            'fields': ('read', 'read_at')
        }),
        ('Metadata', {
            'fields': ('metadata',),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        })
    )

@admin.register(EmailTemplate)
class EmailTemplateAdmin(admin.ModelAdmin):
    list_display = ('name', 'subject', 'is_active', 'created_at')
    list_filter = ('is_active', 'created_at')
    search_fields = ('name', 'subject')
    readonly_fields = ('created_at', 'updated_at')
    
    fieldsets = (
        ('Template Information', {
            'fields': ('name', 'subject', 'is_active')
        }),
        ('Template Content', {
            'fields': ('html_template', 'text_template')
        }),
        ('Variables', {
            'fields': ('variables',),
            'description': 'JSON array of template variables'
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        })
    )
