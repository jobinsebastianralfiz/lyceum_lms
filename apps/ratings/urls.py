from django.urls import path
from . import views

app_name = 'ratings'

urlpatterns = [
    path('course/<int:course_id>/rate/', views.add_rating, name='add_rating'),
    path('course/<int:course_id>/review/', views.add_review, name='add_review'),
    path('course/<int:course_id>/reviews/', views.course_reviews, name='course_reviews'),
    path('review/<int:review_id>/helpful/', views.toggle_helpful, name='toggle_helpful'),
]