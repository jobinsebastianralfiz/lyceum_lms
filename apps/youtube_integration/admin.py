from django.contrib import admin
from django.utils.html import format_html
from .models import YouTubeChannelConfig, YouTubeVideo

@admin.register(YouTubeChannelConfig)
class YouTubeChannelConfigAdmin(admin.ModelAdmin):
    list_display = ('channel_name', 'admin_user', 'channel_id', 'last_sync_at', 'created_at')
    list_filter = ('last_sync_at', 'created_at')
    search_fields = ('channel_name', 'channel_id', 'admin_user__name')
    readonly_fields = ('created_at', 'updated_at')
    
    fieldsets = (
        ('Channel Information', {
            'fields': ('admin_user', 'channel_id', 'channel_name')
        }),
        ('Authentication Tokens', {
            'fields': ('access_token', 'refresh_token'),
            'classes': ('collapse',)
        }),
        ('Sync Information', {
            'fields': ('last_sync_at',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        })
    )

@admin.register(YouTubeVideo)
class YouTubeVideoAdmin(admin.ModelAdmin):
    list_display = ('title', 'video_id', 'channel_config', 'duration_display', 'is_available', 'published_at')
    list_filter = ('channel_config', 'is_available', 'published_at', 'created_at')
    search_fields = ('title', 'video_id', 'description')
    readonly_fields = ('youtube_url', 'created_at', 'updated_at')
    
    def duration_display(self, obj):
        minutes, seconds = divmod(obj.duration, 60)
        hours, minutes = divmod(minutes, 60)
        if hours:
            return f"{hours}:{minutes:02d}:{seconds:02d}"
        return f"{minutes}:{seconds:02d}"
    duration_display.short_description = 'Duration'
    
    fieldsets = (
        ('Video Information', {
            'fields': ('video_id', 'title', 'description', 'youtube_url')
        }),
        ('Media Details', {
            'fields': ('thumbnail_url', 'duration', 'published_at')
        }),
        ('Configuration', {
            'fields': ('channel_config', 'is_available')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        })
    )
