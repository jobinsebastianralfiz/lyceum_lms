from django.db import models
from django.conf import settings


class FeatureConfig(models.Model):
    """
    Stores feature toggle settings for the LMS.
    Uses singleton pattern - only one configuration row exists.
    """

    # Online Learning Features
    enable_online_courses = models.BooleanField(
        default=True,
        help_text="Enable online courses, modules, videos, quizzes, assignments, PDF notes"
    )
    enable_live_sessions = models.BooleanField(
        default=True,
        help_text="Enable live video sessions/classes"
    )

    # Enrollment & Students
    enable_online_enrollment = models.BooleanField(
        default=True,
        help_text="Enable online course enrollments, student progress tracking"
    )
    enable_certificates = models.BooleanField(
        default=True,
        help_text="Enable course completion certificates"
    )

    # Tuition Management (Offline)
    enable_tuition_management = models.BooleanField(
        default=False,
        help_text="Enable offline tuition management - students, batches, attendance, fees"
    )

    # Finance
    enable_finance_management = models.BooleanField(
        default=False,
        help_text="Enable expense & income tracking, vendors, financial reports"
    )
    enable_payments = models.BooleanField(
        default=True,
        help_text="Enable payment processing, installments, tax invoices"
    )

    # Assessments
    enable_assessments = models.BooleanField(
        default=True,
        help_text="Enable assignment submissions, quiz attempts, ratings, reviews"
    )

    # Communications
    enable_notifications = models.BooleanField(
        default=True,
        help_text="Enable push notifications, email templates"
    )

    # Website Content
    enable_website_content = models.BooleanField(
        default=True,
        help_text="Enable news, events, testimonials, placements, banners, leads"
    )

    # Integrations
    enable_youtube_integration = models.BooleanField(
        default=False,
        help_text="Enable YouTube channel sync and video management"
    )

    # Analytics
    enable_analytics = models.BooleanField(
        default=True,
        help_text="Enable mentor dashboard, student analytics, progress alerts"
    )

    # Metadata
    updated_at = models.DateTimeField(auto_now=True)
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='feature_config_updates'
    )

    class Meta:
        verbose_name = "Feature Configuration"
        verbose_name_plural = "Feature Configuration"

    def __str__(self):
        return "Feature Configuration"

    def save(self, *args, **kwargs):
        # Singleton pattern - always use pk=1
        self.pk = 1
        super().save(*args, **kwargs)
        # Clear cache when config changes
        self._clear_cache()

    def delete(self, *args, **kwargs):
        # Prevent deletion of singleton
        pass

    def _clear_cache(self):
        """Clear the feature config cache"""
        from django.core.cache import cache
        cache.delete('feature_config')

    @classmethod
    def get_config(cls):
        """Get or create the singleton config instance"""
        config, created = cls.objects.get_or_create(pk=1)
        return config

    @classmethod
    def get_features_dict(cls):
        """Get features as a dictionary for templates"""
        from django.core.cache import cache

        cache_key = 'feature_config'
        features = cache.get(cache_key)

        if features is None:
            config = cls.get_config()
            features = {
                'online_courses': config.enable_online_courses,
                'live_sessions': config.enable_live_sessions,
                'online_enrollment': config.enable_online_enrollment,
                'certificates': config.enable_certificates,
                'tuition': config.enable_tuition_management,
                'finance': config.enable_finance_management,
                'payments': config.enable_payments,
                'assessments': config.enable_assessments,
                'notifications': config.enable_notifications,
                'website_content': config.enable_website_content,
                'youtube': config.enable_youtube_integration,
                'analytics': config.enable_analytics,
            }
            cache.set(cache_key, features, 300)  # Cache for 5 minutes

        return features
