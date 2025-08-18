from django.urls import path
from . import views

app_name = 'student_portal'

urlpatterns = [
    # Authentication
    path('login/', views.student_login, name='login'),
    path('logout/', views.student_logout, name='logout'),
    
    # Dashboard
    path('', views.dashboard, name='dashboard'),
    
    # Courses
    path('my-courses/', views.my_courses, name='my_courses'),
    path('course/<int:course_id>/', views.course_detail, name='course_detail'),
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
    
    # AJAX endpoints
    path('api/lesson/<int:lesson_id>/progress/', views.update_lesson_progress, name='update_lesson_progress'),
]