from django.urls import path
from . import views

app_name = 'landing'

urlpatterns = [
    path('', views.home, name='home'),
    path('privacy/', views.privacy_policy, name='privacy_policy'),
    path('terms/', views.terms_conditions, name='terms_conditions'),
]