from django.urls import path
from . import views

app_name = 'landing'

urlpatterns = [
    path('', views.home, name='home'),
    path('privacy/', views.privacy_policy, name='privacy_policy'),
    path('terms/', views.terms_conditions, name='terms_conditions'),
    path('contact/', views.contact, name='contact'),
    path('refund-policy/', views.refund_policy, name='refund_policy'),
    path('cancellation-policy/', views.cancellation_policy, name='cancellation_policy'),
    
    # Authentication URLs
    path('login/', views.login_view, name='login'),
    path('register/', views.register, name='register'),
    
    # Public enrollment URLs
    path('courses/', views.courses, name='courses'),
    path('courses/<int:course_id>/', views.course_detail, name='course_detail'),
    path('courses/<int:course_id>/enroll/', views.enroll_course, name='enroll_course'),
    
    # Payment handling URLs
    path('payment/success/', views.payment_success, name='payment_success'),
    path('payment/failed/', views.payment_failed, name='payment_failed'),
]