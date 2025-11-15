from django.urls import path
from . import views

app_name = 'notifications'

urlpatterns = [
    # Notification management
    path('', views.NotificationListView.as_view(), name='notification-list'),
    path('<int:notification_id>/read/', views.mark_notification_read, name='mark-notification-read'),
    path('mark-all-read/', views.mark_all_read, name='mark-all-read'),

    # Device registration for push notifications
    path('register-device/', views.register_device, name='register-device'),
    path('link-device/', views.link_device_to_user, name='link-device'),
    path('unregister-device/', views.unregister_device, name='unregister-device'),
    path('device-status/', views.device_status, name='device-status'),
    path('cleanup-devices/', views.cleanup_user_devices, name='cleanup-devices'),

    # Test endpoint (development only)
    path('test/', views.test_notification, name='test-notification'),
]