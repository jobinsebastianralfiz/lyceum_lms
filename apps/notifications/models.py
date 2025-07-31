from django.db import models
from django.conf import settings

class Notification(models.Model):
    NOTIFICATION_TYPES = [
        ('payment_due', 'Payment Due'),
        ('payment_received', 'Payment Received'),
        ('course_assigned', 'Course Assigned'),
        ('course_completed', 'Course Completed'),
        ('enrollment_confirmed', 'Enrollment Confirmed'),
        ('system_alert', 'System Alert'),
    ]
    
    STATUS_CHOICES = [
        ('sent', 'Sent'),
        ('pending', 'Pending'),
        ('failed', 'Failed'),
    ]
    
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='notifications')
    notification_type = models.CharField(max_length=20, choices=NOTIFICATION_TYPES)
    title = models.CharField(max_length=200)
    message = models.TextField()
    email_sent = models.BooleanField(default=False)
    email_status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='pending')
    read = models.BooleanField(default=False)
    read_at = models.DateTimeField(null=True, blank=True)
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"{self.title} - {self.user.name}"
    
    class Meta:
        db_table = 'notifications'
        ordering = ['-created_at']

class EmailTemplate(models.Model):
    name = models.CharField(max_length=100, unique=True)
    subject = models.CharField(max_length=200)
    html_template = models.TextField()
    text_template = models.TextField(blank=True, null=True)
    variables = models.JSONField(default=list, help_text="List of template variables")
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return self.name
    
    class Meta:
        db_table = 'email_templates'
