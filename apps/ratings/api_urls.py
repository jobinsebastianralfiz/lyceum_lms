from django.urls import path
from . import api_views

app_name = 'ratings_api'

urlpatterns = [
    # Rating endpoints
    path('course/<int:course_id>/ratings/', api_views.CourseRatingListCreateView.as_view(), name='course-ratings'),
    path('course/<int:course_id>/my-rating/', api_views.UserCourseRatingView.as_view(), name='user-course-rating'),
    path('course/<int:course_id>/rating-stats/', api_views.course_rating_stats, name='course-rating-stats'),
    path('course/<int:course_id>/rating-status/', api_views.user_course_rating_status, name='user-rating-status'),
    
    # Review endpoints
    path('course/<int:course_id>/reviews/', api_views.CourseReviewListCreateView.as_view(), name='course-reviews'),
    path('review/<int:review_id>/helpful/', api_views.toggle_review_helpful, name='toggle-review-helpful'),
]