from django.urls import path
from . import views

app_name = 'live_sessions'

urlpatterns = [
    # Student API endpoints
    path('', views.LiveSessionListView.as_view(), name='session-list'),
    path('<int:pk>/', views.LiveSessionDetailView.as_view(), name='session-detail'),
    path('<int:session_id>/join-leave/', views.session_participant_action, name='session-join-leave'),
    path('my-upcoming/', views.my_upcoming_sessions, name='my-upcoming-sessions'),
    path('<int:session_id>/announcements/', views.session_announcements, name='session-announcements'),

    # Admin API endpoints
    path('admin/', views.AdminLiveSessionListView.as_view(), name='admin-session-list'),
    path('admin/<int:pk>/', views.AdminLiveSessionDetailView.as_view(), name='admin-session-detail'),
    path('admin/<int:session_id>/participants/', views.session_participants, name='session-participants'),
    path('admin/<int:session_id>/participants/add/', views.add_session_participant, name='add-session-participant'),
    path('admin/<int:session_id>/participants/<int:participant_id>/remove/', views.remove_session_participant, name='remove-session-participant'),
    path('admin/<int:session_id>/bulk-assign/', views.bulk_assign_participants, name='bulk-assign-participants'),
    path('admin/<int:session_id>/status/', views.session_status_update, name='session-status-update'),
    path('admin/dashboard-stats/', views.dashboard_stats, name='dashboard-stats'),
]