from django.urls import path
from . import views

app_name = 'courses'

urlpatterns = [
    # Course browsing endpoints
    path('categories/', views.CategoryListView.as_view(), name='category-list'),
    path('', views.CourseListView.as_view(), name='course-list'),
    path('<int:pk>/', views.CourseDetailView.as_view(), name='course-detail'),
    path('search/', views.search_courses, name='course-search'),
    
    # Student enrollment endpoints
    path('enrolled/', views.EnrolledCoursesView.as_view(), name='enrolled-courses'),
    
    # Progress tracking endpoints
    path('progress/', views.StudentProgressView.as_view(), name='student-progress'),
    path('module-progress/', views.ModuleProgressView.as_view(), name='module-progress'),
    
    # Assignment endpoints
    path('modules/<int:module_id>/assignments/', views.ModuleAssignmentsView.as_view(), name='module-assignments'),
    path('assignments/<int:pk>/', views.AssignmentDetailView.as_view(), name='assignment-detail'),
    path('assignment-submissions/', views.AssignmentSubmissionView.as_view(), name='assignment-submissions'),
    path('assignment-submissions/<int:pk>/', views.AssignmentSubmissionDetailView.as_view(), name='assignment-submission-detail'),
    
    # Quiz endpoints
    path('modules/<int:module_id>/quizzes/', views.ModuleQuizzesView.as_view(), name='module-quizzes'),
    path('quizzes/<int:pk>/', views.QuizDetailView.as_view(), name='quiz-detail'),
    path('quizzes/<int:quiz_id>/start/', views.StartQuizAttemptView.as_view(), name='start-quiz-attempt'),
    path('quiz-attempts/<int:attempt_id>/submit/', views.SubmitQuizAnswersView.as_view(), name='submit-quiz-answers'),
    path('quiz-attempts/', views.UserQuizAttemptsView.as_view(), name='user-quiz-attempts'),
]