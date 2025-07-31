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
]