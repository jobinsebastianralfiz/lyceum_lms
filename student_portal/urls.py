from django.urls import path
from . import views
from . import student_mentoring_views

app_name = 'student_portal'

urlpatterns = [
    # Authentication  
    path('logout/', views.student_logout, name='logout'),
    
    # Dashboard
    path('', views.dashboard, name='dashboard'),
    
    # Courses
    path('browse-courses/', views.browse_courses, name='browse_courses'),
    path('my-courses/', views.my_courses, name='my_courses'),
    path('course/<int:course_id>/', views.course_detail, name='course_detail'),
    path('course/<int:course_id>/checkout/', views.course_checkout, name='course_checkout'),
    path('lesson/<int:lesson_id>/', views.lesson_viewer, name='lesson_viewer'),
    
    # Profile
    path('profile/', views.profile, name='profile'),
    path('api/change-password/', views.change_password, name='change_password'),
    
    # Assignments
    path('assignment/<int:assignment_id>/', views.assignment_detail, name='assignment_detail'),
    path('api/assignment/<int:assignment_id>/submit/', views.submit_assignment, name='submit_assignment'),
    
    # Quizzes
    path('quiz/<int:quiz_id>/', views.quiz_detail, name='quiz_detail'),
    path('api/quiz/<int:quiz_id>/start/', views.start_quiz_attempt, name='start_quiz_attempt'),
    path('api/quiz-attempt/<int:attempt_id>/submit/', views.submit_quiz_answers, name='submit_quiz_answers'),
    
    # Payments and Invoices
    path('payments/', views.my_payments, name='my_payments'),
    path('payments/<int:enrollment_id>/', views.payment_detail, name='payment_detail'),
    path('invoices/', views.my_invoices, name='my_invoices'),
    path('invoices/<int:invoice_id>/', views.invoice_detail, name='invoice_detail'),
    
    # Payment verification
    path('api/verify-payment/', views.verify_payment, name='verify_payment'),
    
    # Mentoring (Student View)
    path('mentoring/', student_mentoring_views.student_mentoring_dashboard, name='mentoring_dashboard'),
    path('mentoring/sessions/', student_mentoring_views.student_session_history, name='mentoring_sessions'),
    path('mentoring/insights/', student_mentoring_views.student_progress_insights, name='mentoring_insights'),
    
    # AJAX endpoints
    path('api/lesson/<int:lesson_id>/progress/', views.update_lesson_progress, name='update_lesson_progress'),

    # Live Sessions
    path('live-sessions/', views.live_sessions, name='live_sessions'),

    # Settings and Help
    path('settings/', views.settings, name='settings'),
    path('help/', views.help_support, name='help_support'),

    # Certificates
    path('certificates/', views.my_certificates, name='my_certificates'),
    path('certificates/<int:certificate_id>/', views.certificate_view, name='certificate_view'),
    path('certificates/<int:certificate_id>/download/', views.certificate_download, name='certificate_download'),
]