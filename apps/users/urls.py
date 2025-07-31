from django.urls import path
from rest_framework_simplejwt.views import TokenRefreshView
from . import views

app_name = 'users'

urlpatterns = [
    # Authentication endpoints
    path('auth/login/', views.CustomTokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('auth/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('auth/register/', views.UserRegistrationView.as_view(), name='register'),
    path('auth/password-reset/', views.PasswordResetRequestView.as_view(), name='password_reset_request'),
    
    # User profile endpoints
    path('profile/', views.UserProfileView.as_view(), name='profile'),
    path('profile/change-password/', views.PasswordChangeView.as_view(), name='change_password'),
    
    # Team management endpoints
    path('teams/', views.TeamListCreateView.as_view(), name='team-list-create'),
    path('teams/<int:pk>/', views.TeamDetailView.as_view(), name='team-detail'),
    path('teams/<int:team_id>/join/', views.JoinTeamView.as_view(), name='join-team'),
    path('teams/<int:team_id>/leave/', views.LeaveTeamView.as_view(), name='leave-team'),
    path('my-teams/', views.MyTeamsView.as_view(), name='my-teams'),
]