from django.db import models
from django.contrib.auth import get_user_model
from apps.payments.models import Enrollment

User = get_user_model()

class EmailVerification(models.Model):
    """Model to track email verification tokens"""
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='email_verification')
    token = models.CharField(max_length=100, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)
    verified_at = models.DateTimeField(null=True, blank=True)
    is_verified = models.BooleanField(default=False)
    expires_at = models.DateTimeField()

    class Meta:
        app_label = 'emails'

    def __str__(self):
        return f"Email verification for {self.user.email}"
    
    @property
    def is_expired(self):
        from django.utils import timezone
        return timezone.now() > self.expires_at
    
    def verify(self):
        """Mark email as verified"""
        from django.utils import timezone
        self.is_verified = True
        self.verified_at = timezone.now()
        self.save()
        
        # Also update user model if it has email_verified field
        if hasattr(self.user, 'email_verified'):
            self.user.email_verified = True
            self.user.save()


class EmailTemplate(models.Model):
    """Email templates for different purposes"""
    TEMPLATE_CHOICES = [
        ('verification', 'Email Verification'),
        ('welcome', 'Welcome Email'),
        ('invoice', 'Tax Invoice'),
        ('enrollment_confirmation', 'Enrollment Confirmation'),
        ('password_reset', 'Password Reset'),
    ]
    
    name = models.CharField(max_length=100)
    template_type = models.CharField(max_length=50, choices=TEMPLATE_CHOICES)
    subject = models.CharField(max_length=200)
    html_content = models.TextField()
    text_content = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"{self.name} ({self.template_type})"
    
    class Meta:
        app_label = 'emails'
        unique_together = ['template_type']


class SentEmail(models.Model):
    """Track all sent emails"""
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('sent', 'Sent'),
        ('delivered', 'Delivered'),
        ('failed', 'Failed'),
        ('bounced', 'Bounced'),
    ]
    
    recipient_email = models.EmailField()
    recipient_name = models.CharField(max_length=100, blank=True)
    sender_email = models.EmailField()
    subject = models.CharField(max_length=200)
    template_type = models.CharField(max_length=50, blank=True)
    sendgrid_message_id = models.CharField(max_length=100, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    sent_at = models.DateTimeField(null=True, blank=True)
    delivered_at = models.DateTimeField(null=True, blank=True)
    failed_reason = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    # Optional foreign keys
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    enrollment = models.ForeignKey(Enrollment, on_delete=models.SET_NULL, null=True, blank=True)
    
    def __str__(self):
        return f"Email to {self.recipient_email} - {self.subject}"
    
    class Meta:
        app_label = 'emails'
        ordering = ['-created_at']
