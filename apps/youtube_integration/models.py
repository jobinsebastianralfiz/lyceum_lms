from django.db import models
from django.conf import settings

class YouTubeChannelConfig(models.Model):
    admin_user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='youtube_configs')
    channel_id = models.CharField(max_length=50)
    channel_name = models.CharField(max_length=200)
    access_token = models.TextField()
    refresh_token = models.TextField()
    last_sync_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"{self.channel_name} ({self.admin_user.name})"
    
    class Meta:
        db_table = 'youtube_channel_configs'
        unique_together = ['admin_user', 'channel_id']

class YouTubeVideo(models.Model):
    video_id = models.CharField(max_length=20, unique=True)
    title = models.CharField(max_length=300)
    description = models.TextField(blank=True, null=True)
    thumbnail_url = models.URLField()
    duration = models.PositiveIntegerField(help_text="Duration in seconds")
    published_at = models.DateTimeField()
    channel_config = models.ForeignKey(YouTubeChannelConfig, on_delete=models.CASCADE, related_name='videos')
    is_available = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return self.title
    
    @property
    def youtube_url(self):
        return f"https://www.youtube.com/watch?v={self.video_id}"
    
    class Meta:
        db_table = 'youtube_videos'
