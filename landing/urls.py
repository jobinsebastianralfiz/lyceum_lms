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
    path('courses/<int:course_id>/enquiry/', views.course_enquiry, name='course_enquiry'),

    # Payment handling URLs
    path('payment/success/', views.payment_success, name='payment_success'),
    path('payment/failed/', views.payment_failed, name='payment_failed'),

    # News URLs
    path('news/', views.news_list, name='news_list'),
    path('news/<slug:slug>/', views.news_detail, name='news_detail'),

    # Events URLs
    path('events/', views.events_list, name='events_list'),
    path('events/<slug:slug>/', views.event_detail, name='event_detail'),

    # Testimonials URLs
    path('testimonials/', views.testimonials_list, name='testimonials_list'),
    path('testimonials/<int:pk>/', views.testimonial_detail, name='testimonial_detail'),

    # Placements (Success Stories) URLs
    path('placements/', views.placements_list, name='placements_list'),
    path('placements/<int:pk>/', views.placement_detail, name='placement_detail'),

    # Achievements URLs
    path('achievements/', views.achievements_list, name='achievements_list'),
    path('achievements/<slug:slug>/', views.achievement_detail, name='achievement_detail'),
]