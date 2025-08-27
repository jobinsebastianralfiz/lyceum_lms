from django.urls import path
from . import mentor_views

app_name = 'mentor'

urlpatterns = [
    # Mentor Dashboard
    path('mentor/', mentor_views.mentor_dashboard, name='mentor_dashboard'),
    
    # Student Analytics
    path('mentor/students/', mentor_views.student_analytics_list, name='student_analytics_list'),
    path('mentor/student/<int:student_id>/', mentor_views.student_detail, name='student_detail'),
    
    # Alerts Management
    path('mentor/alerts/', mentor_views.alerts_list, name='alerts_list'),
    path('mentor/alerts/<int:alert_id>/resolve/', mentor_views.resolve_alert, name='resolve_alert'),
    
    # Mentoring Sessions
    path('mentor/sessions/create/', mentor_views.create_mentor_session, name='create_mentor_session'),
    
    # Debug test
    path('mentor/test/', mentor_views.mentor_test, name='mentor_test'),
]