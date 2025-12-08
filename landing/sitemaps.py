from django.contrib.sitemaps import Sitemap
from django.urls import reverse
from apps.courses.models import Course
from apps.content_management.models import News, Event, Testimonial, Placement, Achievement


class StaticViewSitemap(Sitemap):
    """Sitemap for static pages."""
    priority = 0.8
    changefreq = 'weekly'
    protocol = 'https'

    def items(self):
        return [
            'landing:home',
            'landing:courses',
            'landing:contact',
            'landing:login',
            'landing:register',
            'landing:privacy_policy',
            'landing:terms_conditions',
            'landing:refund_policy',
            'landing:cancellation_policy',
        ]

    def location(self, item):
        return reverse(item)


class CourseSitemap(Sitemap):
    """Sitemap for course pages."""
    changefreq = 'weekly'
    priority = 0.9
    protocol = 'https'

    def items(self):
        return Course.objects.filter(is_published=True)

    def lastmod(self, obj):
        return obj.updated_at

    def location(self, obj):
        return reverse('landing:course_detail', kwargs={'course_id': obj.id})


class NewsSitemap(Sitemap):
    """Sitemap for news articles."""
    changefreq = 'daily'
    priority = 0.7
    protocol = 'https'

    def items(self):
        return News.objects.filter(is_published=True)

    def lastmod(self, obj):
        return obj.updated_at if hasattr(obj, 'updated_at') else obj.created_at

    def location(self, obj):
        return reverse('landing:news_detail', kwargs={'slug': obj.slug})


class EventSitemap(Sitemap):
    """Sitemap for events."""
    changefreq = 'weekly'
    priority = 0.6
    protocol = 'https'

    def items(self):
        return Event.objects.filter(is_published=True)

    def lastmod(self, obj):
        return obj.updated_at if hasattr(obj, 'updated_at') else obj.created_at

    def location(self, obj):
        return reverse('landing:event_detail', kwargs={'slug': obj.slug})
