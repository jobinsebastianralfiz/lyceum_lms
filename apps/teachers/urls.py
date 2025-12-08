from django.urls import path
from . import views

app_name = 'teachers'

urlpatterns = [
    # ============== Authentication APIs ==============
    path('auth/login/', views.TeacherLoginView.as_view(), name='teacher-login'),
    path('auth/change-password/', views.TeacherChangePasswordView.as_view(), name='teacher-change-password'),
    path('auth/forgot-password/', views.TeacherForgotPasswordView.as_view(), name='teacher-forgot-password'),
    path('auth/reset-password/', views.TeacherResetPasswordView.as_view(), name='teacher-reset-password'),

    # ============== Profile APIs ==============
    path('profile/', views.TeacherProfileView.as_view(), name='teacher-profile'),

    # ============== Dashboard APIs ==============
    path('dashboard/', views.TeacherDashboardView.as_view(), name='teacher-dashboard'),

    # ============== Course APIs ==============
    path('courses/', views.TeacherCourseListView.as_view(), name='teacher-courses'),
    path('courses/<int:course_id>/', views.TeacherCourseDetailView.as_view(), name='teacher-course-detail'),
    path('courses/<int:course_id>/students/', views.TeacherCourseStudentsView.as_view(), name='teacher-course-students'),

    # ============== Student APIs ==============
    path('students/', views.TeacherAllStudentsView.as_view(), name='teacher-all-students'),
    path('students/<int:student_id>/', views.TeacherStudentDetailView.as_view(), name='teacher-student-detail'),
    path('students/<int:student_id>/progress/', views.TeacherStudentProgressView.as_view(), name='teacher-student-progress'),

    # ============== Assignment APIs ==============
    path('assignments/', views.TeacherAssignmentListView.as_view(), name='teacher-assignments'),
    path('assignments/<int:assignment_id>/submissions/', views.TeacherAssignmentSubmissionsView.as_view(), name='teacher-assignment-submissions'),
    path('submissions/<int:submission_id>/grade/', views.TeacherGradeSubmissionView.as_view(), name='teacher-grade-submission'),

    # ============== Quiz APIs ==============
    path('quizzes/', views.TeacherQuizListView.as_view(), name='teacher-quizzes'),
    path('quizzes/<int:quiz_id>/attempts/', views.TeacherQuizAttemptsView.as_view(), name='teacher-quiz-attempts'),
    path('quizzes/<int:quiz_id>/analytics/', views.TeacherQuizAnalyticsView.as_view(), name='teacher-quiz-analytics'),

    # ============== Schedule APIs ==============
    path('schedule/', views.TeacherScheduleListView.as_view(), name='teacher-schedule'),

    # ============== Announcement APIs ==============
    path('announcements/', views.TeacherAnnouncementListView.as_view(), name='teacher-announcements'),
    path('announcements/<int:pk>/', views.TeacherAnnouncementDetailView.as_view(), name='teacher-announcement-detail'),
]

# Admin teacher management URLs (to be included in admin urls)
admin_teacher_urlpatterns = [
    path('teachers/', views.AdminTeacherListView.as_view(), name='admin-teachers'),
    path('teachers/<int:pk>/', views.AdminTeacherDetailView.as_view(), name='admin-teacher-detail'),
    path('teachers/<int:pk>/assign-courses/', views.AdminTeacherAssignCoursesView.as_view(), name='admin-teacher-assign-courses'),
    path('teachers/<int:pk>/reset-password/', views.AdminTeacherResetPasswordView.as_view(), name='admin-teacher-reset-password'),
]
