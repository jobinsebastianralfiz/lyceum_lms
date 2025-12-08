"""
URL configuration for CodeLearn LMS project.
"""
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView, SpectacularRedocView
from .admin import admin_site

urlpatterns = [
    # Landing Pages
    path('', include('landing.urls')),
    
    # Email System
    path('', include('emails.urls')),
    
    # Student Portal
    path('student/', include('student_portal.urls')),

    # Teacher Portal
    path('teacher/', include('teacher_portal.urls')),

    # Mentor Dashboard
    path('', include('apps.courses.mentor_urls')),
    
    # Custom Admin Interface
    path('admin/', include('apps.custom_admin.urls')),
    
    # Ratings System
    path('ratings/', include('apps.ratings.urls')),
    
    # Django Default Admin (fallback)
    path('django-admin/', admin_site.urls),
    
    # API Documentation
    path('api/schema/', SpectacularAPIView.as_view(), name='schema'),
    path('api/docs/', SpectacularSwaggerView.as_view(url_name='schema'), name='swagger-ui'),
    path('api/redoc/', SpectacularRedocView.as_view(url_name='schema'), name='redoc'),
    
    # API Endpoints
    path('api/users/', include('apps.users.urls')),
    path('api/courses/', include('apps.courses.urls')),
    path('api/payments/', include('apps.payments.urls')),
    path('api/notifications/', include('apps.notifications.urls')),
    path('api/ratings/', include('apps.ratings.api_urls')),
    path('api/youtube/', include('apps.youtube_integration.urls')),
    path('api/content/', include('apps.content_management.urls')),
    path('api/live-sessions/', include('apps.live_sessions.urls')),
    path('api/teacher/', include('apps.teachers.urls')),
]

# Serve media files in development
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
else:
    # In production, serve static and media files through Django since web server config isn't working
    from django.views.static import serve
    from django.urls import re_path
    
    urlpatterns += [
        re_path(r'^codelearnstatic/(?P<path>.*)$', serve, {
            'document_root': settings.STATIC_ROOT,
        }),
        re_path(r'^codelearnmedia/(?P<path>.*)$', serve, {
            'document_root': settings.MEDIA_ROOT,
        }),
    ]
