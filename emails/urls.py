from django.urls import path
from . import views

app_name = 'emails'

urlpatterns = [
    path('verify-email/<str:token>/', views.verify_email, name='verify_email'),
    path('verification-status/', views.verification_status, name='verification_status'),
]