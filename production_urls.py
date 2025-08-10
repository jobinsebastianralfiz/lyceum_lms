"""
URL configuration for CodeLearn LMS project - Production Version
Upload this as urls.py to your production server
"""
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView, SpectacularRedocView
from .admin import admin_site

urlpatterns = [
    # Custom Admin Interface
    path('admin/', include('apps.custom_admin.urls')),
    
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
    path('api/youtube/', include('apps.youtube_integration.urls')),
]

# In production, Apache serves static files via .htaccess
# But we still need to ensure Django doesn't interfere
# Remove the DEBUG check so static URLs are always properly handled
urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)