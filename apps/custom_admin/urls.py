from django.urls import path
from . import views

app_name = 'custom_admin'

urlpatterns = [
    # Authentication
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    
    # Dashboard
    path('', views.dashboard_view, name='dashboard'),
    
    # COURSES
    path('categories/', views.categories_list_view, name='categories_list'),
    path('categories/add/', views.category_create_view, name='category_create'),
    path('categories/<int:category_id>/edit/', views.category_edit_view, name='category_edit'),
    path('categories/<int:category_id>/delete/', views.category_delete_view, name='category_delete'),
    
    path('courses/', views.courses_list_view, name='courses_list'),
    path('courses/add/', views.course_create_view, name='course_create'),
    path('courses/<int:course_id>/', views.course_detail_view, name='course_detail'),
    path('courses/<int:course_id>/edit/', views.course_edit_view, name='course_edit'),
    path('courses/<int:course_id>/delete/', views.course_delete_view, name='course_delete'),
    
    path('modules/', views.modules_list_view, name='modules_list'),
    path('modules/add/', views.module_create_view, name='module_create'),
    path('modules/<int:module_id>/edit/', views.module_edit_view, name='module_edit'),
    path('modules/<int:module_id>/delete/', views.module_delete_view, name='module_delete'),
    
    path('student-progress/', views.student_progress_list_view, name='student_progress_list'),
    
    path('video-lessons/', views.video_lessons_list_view, name='video_lessons_list'),
    path('video-lessons/add/', views.video_lesson_create_view, name='video_lesson_create'),
    path('video-lessons/<int:lesson_id>/edit/', views.video_lesson_edit_view, name='video_lesson_edit'),
    path('video-lessons/<int:lesson_id>/delete/', views.video_lesson_delete_view, name='video_lesson_delete'),
    
    # NOTIFICATIONS
    path('email-templates/', views.email_templates_list_view, name='email_templates_list'),
    path('email-templates/add/', views.email_template_create_view, name='email_template_create'),
    path('email-templates/<int:template_id>/edit/', views.email_template_edit_view, name='email_template_edit'),
    path('email-templates/<int:template_id>/delete/', views.email_template_delete_view, name='email_template_delete'),
    
    path('notifications/', views.notifications_list_view, name='notifications_list'),
    path('notifications/add/', views.notification_create_view, name='notification_create'),
    path('notifications/<int:notification_id>/edit/', views.notification_edit_view, name='notification_edit'),
    path('notifications/<int:notification_id>/delete/', views.notification_delete_view, name='notification_delete'),
    
    # PAYMENTS
    path('enrollments/', views.enrollments_list_view, name='enrollments_list'),
    path('enrollments/add/', views.enrollment_create_view, name='enrollment_create'),
    path('enrollments/<int:enrollment_id>/edit/', views.enrollment_edit_view, name='enrollment_edit'),
    path('enrollments/<int:enrollment_id>/delete/', views.enrollment_delete_view, name='enrollment_delete'),
    
    path('installment-plans/', views.installment_plans_list_view, name='installment_plans_list'),
    path('installment-plans/add/', views.installment_plan_create_view, name='installment_plan_create'),
    path('installment-plans/<int:plan_id>/edit/', views.installment_plan_edit_view, name='installment_plan_edit'),
    path('installment-plans/<int:plan_id>/delete/', views.installment_plan_delete_view, name='installment_plan_delete'),
    
    path('payments/', views.payments_list_view, name='payments_list'),
    path('payments/add/', views.payment_create_view, name='payment_create'),
    path('payments/<int:payment_id>/edit/', views.payment_edit_view, name='payment_edit'),
    path('payments/<int:payment_id>/delete/', views.payment_delete_view, name='payment_delete'),
    
    path('tax-invoices/', views.tax_invoices_list_view, name='tax_invoices_list'),
    path('tax-invoices/add/', views.tax_invoice_create_view, name='tax_invoice_create'),
    path('tax-invoices/<int:invoice_id>/edit/', views.tax_invoice_edit_view, name='tax_invoice_edit'),
    path('tax-invoices/<int:invoice_id>/delete/', views.tax_invoice_delete_view, name='tax_invoice_delete'),
    
    # USERS
    path('team-memberships/', views.team_memberships_list_view, name='team_memberships_list'),
    path('team-memberships/add/', views.team_membership_create_view, name='team_membership_create'),
    path('team-memberships/<int:membership_id>/edit/', views.team_membership_edit_view, name='team_membership_edit'),
    path('team-memberships/<int:membership_id>/delete/', views.team_membership_delete_view, name='team_membership_delete'),
    
    path('teams/', views.teams_list_view, name='teams_list'),
    path('teams/add/', views.team_create_view, name='team_create'),
    path('teams/<int:team_id>/edit/', views.team_edit_view, name='team_edit'),
    path('teams/<int:team_id>/delete/', views.team_delete_view, name='team_delete'),
    
    path('users/', views.users_list_view, name='users_list'),
    path('users/add/', views.user_create_view, name='user_create'),
    path('users/<int:user_id>/', views.user_detail_view, name='user_detail'),
    path('users/<int:user_id>/edit/', views.user_edit_view, name='user_edit'),
    path('users/<int:user_id>/delete/', views.user_delete_view, name='user_delete'),
    
    # YOUTUBE INTEGRATION
    path('youtube-channel-configs/', views.youtube_channel_configs_list_view, name='youtube_channel_configs_list'),
    path('youtube-channel-configs/add/', views.youtube_channel_config_create_view, name='youtube_channel_config_create'),
    path('youtube-channel-configs/<int:config_id>/edit/', views.youtube_channel_config_edit_view, name='youtube_channel_config_edit'),
    path('youtube-channel-configs/<int:config_id>/delete/', views.youtube_channel_config_delete_view, name='youtube_channel_config_delete'),
    
    path('youtube-videos/', views.youtube_videos_list_view, name='youtube_videos_list'),
    path('youtube-videos/add/', views.youtube_video_create_view, name='youtube_video_create'),
    path('youtube-videos/<int:video_id>/edit/', views.youtube_video_edit_view, name='youtube_video_edit'),
    path('youtube-videos/<int:video_id>/delete/', views.youtube_video_delete_view, name='youtube_video_delete'),
]