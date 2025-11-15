from django.db import models
from django.conf import settings
from encrypted_model_fields.fields import EncryptedTextField, EncryptedCharField
from django.utils import timezone


class SystemSetting(models.Model):
    """Encrypted system settings stored in database"""

    CATEGORY_CHOICES = [
        ('email', 'Email Settings'),
        ('payment', 'Payment Gateway'),
        ('google', 'Google Services'),
        ('firebase', 'Firebase/FCM'),
        ('storage', 'Storage (AWS/S3)'),
        ('sms', 'SMS Service'),
        ('security', 'Security'),
        ('general', 'General Settings'),
    ]

    key = models.CharField(
        max_length=255,
        unique=True,
        help_text="Setting key (e.g., RAZORPAY_KEY_ID)"
    )
    value = EncryptedTextField(
        help_text="Encrypted value of the setting"
    )
    category = models.CharField(
        max_length=50,
        choices=CATEGORY_CHOICES,
        help_text="Category of the setting"
    )
    description = models.TextField(
        blank=True,
        help_text="Description of what this setting is for"
    )
    is_sensitive = models.BooleanField(
        default=True,
        help_text="If true, value will be masked in admin UI"
    )
    is_active = models.BooleanField(
        default=True,
        help_text="If false, system will fall back to environment variable"
    )

    # Audit fields
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='updated_settings'
    )

    class Meta:
        db_table = 'system_settings'
        ordering = ['category', 'key']
        verbose_name = 'System Setting'
        verbose_name_plural = 'System Settings'

    def __str__(self):
        return f"{self.key} ({self.category})"

    def get_masked_value(self):
        """Return masked value for display"""
        if self.is_sensitive and self.value:
            # Show first 4 and last 4 characters
            if len(self.value) > 12:
                return f"{self.value[:4]}...{self.value[-4:]}"
            else:
                return "*" * len(self.value)
        return self.value


class SettingChangeLog(models.Model):
    """Audit log for setting changes"""

    setting = models.ForeignKey(
        SystemSetting,
        on_delete=models.CASCADE,
        related_name='change_logs'
    )
    changed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True
    )
    old_value = EncryptedTextField(blank=True, null=True)
    new_value = EncryptedTextField(blank=True, null=True)
    change_reason = models.TextField(blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True)
    changed_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'setting_change_logs'
        ordering = ['-changed_at']
        verbose_name = 'Setting Change Log'
        verbose_name_plural = 'Setting Change Logs'

    def __str__(self):
        return f"{self.setting.key} changed by {self.changed_by} at {self.changed_at}"


class GoogleWorkspaceIntegration(models.Model):
    """Store Google Workspace OAuth credentials"""

    admin_user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='google_workspace'
    )
    google_email = models.EmailField(
        help_text="Google Workspace email address"
    )
    access_token = EncryptedTextField(
        help_text="OAuth access token (encrypted)"
    )
    refresh_token = EncryptedTextField(
        help_text="OAuth refresh token (encrypted)"
    )
    token_expires_at = models.DateTimeField(
        help_text="When the access token expires"
    )
    scopes = models.JSONField(
        default=list,
        help_text="List of granted OAuth scopes"
    )
    is_active = models.BooleanField(
        default=True,
        help_text="If false, integration is disabled"
    )

    # Tracking
    connected_at = models.DateTimeField(auto_now_add=True)
    last_refreshed = models.DateTimeField(auto_now=True)
    last_used = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = 'google_workspace_integrations'
        verbose_name = 'Google Workspace Integration'
        verbose_name_plural = 'Google Workspace Integrations'

    def __str__(self):
        return f"Google Workspace: {self.google_email}"

    def is_token_expired(self):
        """Check if access token is expired"""
        return timezone.now() >= self.token_expires_at

    def mark_used(self):
        """Update last used timestamp"""
        self.last_used = timezone.now()
        self.save(update_fields=['last_used'])


class GoogleMeetSession(models.Model):
    """Extended info for Google Meet sessions"""

    live_session = models.OneToOneField(
        'live_sessions.LiveSession',
        on_delete=models.CASCADE,
        related_name='google_meet_info'
    )
    google_event_id = models.CharField(
        max_length=255,
        unique=True,
        help_text="Google Calendar event ID"
    )
    google_meet_code = models.CharField(
        max_length=50,
        help_text="Meeting code (e.g., abc-defg-hij)"
    )
    calendar_link = models.URLField(
        help_text="Link to Google Calendar event"
    )
    hangout_link = models.URLField(
        help_text="Google Meet join link"
    )

    # Settings
    recording_enabled = models.BooleanField(
        default=False,
        help_text="Whether recording is enabled for this meeting"
    )
    waiting_room_enabled = models.BooleanField(
        default=True,
        help_text="Whether waiting room is enabled"
    )

    # Recordings
    recording_urls = models.JSONField(
        default=list,
        blank=True,
        help_text="List of recording URLs (if any)"
    )

    # Tracking
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='created_google_meets'
    )

    class Meta:
        db_table = 'google_meet_sessions'
        verbose_name = 'Google Meet Session'
        verbose_name_plural = 'Google Meet Sessions'

    def __str__(self):
        return f"Google Meet: {self.live_session.title}"
