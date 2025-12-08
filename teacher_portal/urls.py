from django.urls import path
from . import views

app_name = 'teacher_portal'

urlpatterns = [
    # Dashboard
    path('', views.dashboard, name='dashboard'),

    # Courses
    path('courses/', views.my_courses, name='my_courses'),
    path('courses/<int:course_id>/', views.course_detail, name='course_detail'),
    path('courses/<int:course_id>/students/', views.course_students, name='course_students'),
    path('courses/<int:course_id>/assignments/', views.course_assignments, name='course_assignments'),
    path('courses/<int:course_id>/quizzes/', views.course_quizzes, name='course_quizzes'),

    # Students
    path('students/', views.my_students, name='my_students'),
    path('students/<int:student_id>/', views.student_detail, name='student_detail'),

    # Assignments
    path('assignments/', views.assignments, name='assignments'),
    path('assignments/<int:assignment_id>/submissions/', views.assignment_submissions, name='assignment_submissions'),
    path('submissions/<int:submission_id>/grade/', views.grade_submission, name='grade_submission'),

    # Quizzes
    path('quizzes/', views.quizzes, name='quizzes'),
    path('quizzes/<int:quiz_id>/attempts/', views.quiz_attempts, name='quiz_attempts'),

    # Schedule
    path('schedule/', views.my_schedule, name='my_schedule'),

    # Live Sessions
    path('live-sessions/', views.live_sessions, name='live_sessions'),
    path('live-sessions/<int:session_id>/', views.live_session_detail, name='live_session_detail'),

    # Announcements
    path('announcements/', views.announcements, name='announcements'),
    path('announcements/create/', views.create_announcement, name='create_announcement'),
    path('announcements/<int:announcement_id>/edit/', views.edit_announcement, name='edit_announcement'),
    path('announcements/<int:announcement_id>/delete/', views.delete_announcement, name='delete_announcement'),

    # Profile
    path('profile/', views.my_profile, name='my_profile'),
    path('profile/update/', views.update_profile, name='update_profile'),
    path('profile/password/', views.change_password, name='change_password'),

    # Logout
    path('logout/', views.teacher_logout, name='logout'),
]
