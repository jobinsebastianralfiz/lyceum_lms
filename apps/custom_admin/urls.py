from django.urls import path
from . import views
from . import rating_views
from apps.content_management import admin_views

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
    path('courses/<int:course_id>/add-module/', views.course_add_module_view, name='course_add_module'),
    path('courses/<int:course_id>/remove-module/<int:course_module_id>/', views.course_remove_module_view, name='course_remove_module'),
    path('courses/<int:course_id>/reorder-modules/', views.course_reorder_modules_view, name='course_reorder_modules'),
    path('courses/<int:course_id>/add-assignment/', views.course_add_assignment_view, name='course_add_assignment'),
    path('courses/<int:course_id>/remove-assignment/<int:course_assignment_id>/', views.course_remove_assignment_view, name='course_remove_assignment'),
    path('courses/<int:course_id>/add-quiz/', views.course_add_quiz_view, name='course_add_quiz'),
    path('courses/<int:course_id>/remove-quiz/<int:course_quiz_id>/', views.course_remove_quiz_view, name='course_remove_quiz'),
    path('courses/<int:course_id>/add-pdf/', views.course_add_pdf_view, name='course_add_pdf'),
    path('courses/<int:course_id>/remove-pdf/<int:course_pdf_id>/', views.course_remove_pdf_view, name='course_remove_pdf'),

    path('modules/', views.modules_list_view, name='modules_list'),
    path('modules/<int:module_id>/', views.module_detail_view, name='module_detail'),
    path('modules/add/', views.module_create_view, name='module_create'),
    path('modules/<int:module_id>/edit/', views.module_edit_view, name='module_edit'),
    path('modules/<int:module_id>/delete/', views.module_delete_view, name='module_delete'),
    path('modules/<int:module_id>/add-video/', views.module_add_video_view, name='module_add_video'),
    path('modules/<int:module_id>/remove-video/<int:module_video_id>/', views.module_remove_video_view, name='module_remove_video'),
    path('modules/<int:module_id>/add-assignment/', views.module_add_assignment_view, name='module_add_assignment'),
    path('modules/<int:module_id>/remove-assignment/<int:module_assignment_id>/', views.module_remove_assignment_view, name='module_remove_assignment'),
    path('modules/<int:module_id>/add-quiz/', views.module_add_quiz_view, name='module_add_quiz'),
    path('modules/<int:module_id>/remove-quiz/<int:module_quiz_id>/', views.module_remove_quiz_view, name='module_remove_quiz'),
    path('modules/<int:module_id>/bulk-delete-videos/', views.module_bulk_delete_videos_view, name='module_bulk_delete_videos'),
    path('modules/<int:module_id>/bulk-delete-assignments/', views.module_bulk_delete_assignments_view, name='module_bulk_delete_assignments'),
    path('modules/<int:module_id>/bulk-delete-quizzes/', views.module_bulk_delete_quizzes_view, name='module_bulk_delete_quizzes'),
    path('modules/<int:module_id>/reorder-videos/', views.module_reorder_videos_view, name='module_reorder_videos'),
    path('modules/<int:module_id>/reorder-assignments/', views.module_reorder_assignments_view, name='module_reorder_assignments'),
    path('modules/<int:module_id>/reorder-quizzes/', views.module_reorder_quizzes_view, name='module_reorder_quizzes'),
    
    path('student-progress/', views.student_progress_list_view, name='student_progress_list'),
    
    path('video-lessons/', views.video_lessons_list_view, name='video_lessons_list'),
    path('video-lessons/add/', views.video_lesson_create_view, name='video_lesson_create'),
    path('video-lessons/<int:lesson_id>/edit/', views.video_lesson_edit_view, name='video_lesson_edit'),
    path('video-lessons/<int:lesson_id>/delete/', views.video_lesson_delete_view, name='video_lesson_delete'),
    
    # Enhanced Video Management AJAX endpoints
    path('video-fetch-metadata/', views.video_fetch_metadata_view, name='video_fetch_metadata'),
    path('video-lessons/<int:lesson_id>/sync/', views.video_sync_metadata_view, name='video_sync_metadata'),
    
    # ASSIGNMENTS
    path('assignments/', views.assignments_list_view, name='assignments_list'),
    path('assignments/<int:assignment_id>/', views.assignment_detail_view, name='assignment_detail'),
    path('assignments/add/', views.assignment_create_view, name='assignment_create'),
    path('assignments/<int:assignment_id>/edit/', views.assignment_edit_view, name='assignment_edit'),
    path('assignments/<int:assignment_id>/delete/', views.assignment_delete_view, name='assignment_delete'),
    
    # ASSIGNMENT SUBMISSIONS  
    path('assignment-submissions/', views.assignment_submissions_list_view, name='assignment_submissions_list'),
    path('assignment-submissions/<int:submission_id>/', views.assignment_submission_detail_view, name='assignment_submission_detail'),
    
    # QUIZZES
    path('quizzes/', views.quizzes_list_view, name='quizzes_list'),
    path('quizzes/<int:quiz_id>/', views.quiz_detail_view, name='quiz_detail'),
    path('quizzes/add/', views.quiz_create_view, name='quiz_create'),
    path('quizzes/<int:quiz_id>/edit/', views.quiz_edit_view, name='quiz_edit'),
    path('quizzes/<int:quiz_id>/delete/', views.quiz_delete_view, name='quiz_delete'),
    
    # QUIZ QUESTIONS
    path('quiz-questions/', views.quiz_questions_list_view, name='quiz_questions_list'),
    path('quiz-questions/<int:question_id>/', views.quiz_question_detail_view, name='quiz_question_detail'),
    path('quiz-questions/add/', views.quiz_question_create_view, name='quiz_question_create'),
    path('quiz-questions/<int:question_id>/edit/', views.quiz_question_edit_view, name='quiz_question_edit'),
    path('quiz-questions/<int:question_id>/delete/', views.quiz_question_delete_view, name='quiz_question_delete'),
    
    # QUIZ CHOICES
    path('quiz-choices/', views.quiz_choices_list_view, name='quiz_choices_list'),
    path('quiz-choices/add/', views.quiz_choice_create_view, name='quiz_choice_create'),
    path('quiz-choices/<int:choice_id>/edit/', views.quiz_choice_edit_view, name='quiz_choice_edit'),
    path('quiz-choices/<int:choice_id>/delete/', views.quiz_choice_delete_view, name='quiz_choice_delete'),
    
    # QUIZ ATTEMPTS
    path('quiz-attempts/', views.quiz_attempts_list_view, name='quiz_attempts_list'),
    path('quiz-attempts/<int:attempt_id>/', views.quiz_attempt_detail_view, name='quiz_attempt_detail'),
    path('quiz-attempts/<int:attempt_id>/delete/', views.quiz_attempt_delete_view, name='quiz_attempt_delete'),
    path('quizzes/<int:quiz_id>/reset-attempts/', views.quiz_attempt_reset_view, name='quiz_attempt_reset'),

    # PDF NOTES
    path('pdf-notes/', views.pdf_notes_list_view, name='pdf_notes_list'),
    path('pdf-notes/add/', views.pdf_note_create_view, name='pdf_note_create'),
    path('pdf-notes/<int:pdf_id>/edit/', views.pdf_note_edit_view, name='pdf_note_edit'),
    path('pdf-notes/<int:pdf_id>/delete/', views.pdf_note_delete_view, name='pdf_note_delete'),

    # MODULE PROGRESS
    path('module-progress/', views.module_progress_list_view, name='module_progress_list'),
    path('module-progress/<int:progress_id>/', views.module_progress_detail_view, name='module_progress_detail'),
    
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
    path('users/bulk-delete/', views.users_bulk_delete_view, name='users_bulk_delete'),
    
    # YOUTUBE INTEGRATION
    path('youtube-channel-configs/', views.youtube_channel_configs_list_view, name='youtube_channel_configs_list'),
    path('youtube-channel-configs/add/', views.youtube_channel_config_create_view, name='youtube_channel_config_create'),
    path('youtube-channel-configs/<int:config_id>/edit/', views.youtube_channel_config_edit_view, name='youtube_channel_config_edit'),
    path('youtube-channel-configs/<int:config_id>/delete/', views.youtube_channel_config_delete_view, name='youtube_channel_config_delete'),
    
    path('youtube-videos/', views.youtube_videos_list_view, name='youtube_videos_list'),
    path('youtube-videos/add/', views.youtube_video_create_view, name='youtube_video_create'),
    path('youtube-videos/<int:video_id>/edit/', views.youtube_video_edit_view, name='youtube_video_edit'),
    path('youtube-videos/<int:video_id>/delete/', views.youtube_video_delete_view, name='youtube_video_delete'),
    
    # RATINGS & REVIEWS
    path('ratings/', rating_views.ratings_list_view, name='ratings_list'),
    path('ratings/<int:rating_id>/delete/', rating_views.rating_delete_view, name='rating_delete'),
    path('ratings/bulk-delete/', rating_views.ratings_bulk_delete_view, name='ratings_bulk_delete'),
    
    path('reviews/', rating_views.reviews_list_view, name='reviews_list'),
    path('reviews/<int:review_id>/', rating_views.review_detail_view, name='review_detail'),
    path('reviews/<int:review_id>/approve/', rating_views.review_approve_view, name='review_approve'),
    path('reviews/<int:review_id>/reject/', rating_views.review_reject_view, name='review_reject'),
    path('reviews/<int:review_id>/delete/', rating_views.review_delete_view, name='review_delete'),
    path('reviews/bulk-moderate/', rating_views.reviews_bulk_moderate_view, name='reviews_bulk_moderate'),
    
    path('review-votes/', rating_views.review_votes_list_view, name='review_votes_list'),

    # CONTENT MANAGEMENT
    path('content/', admin_views.content_dashboard_view, name='content_dashboard'),
    
    # LEADS MANAGEMENT
    path('content/leads/', admin_views.leads_list_view, name='leads_list'),
    path('content/leads/<int:lead_id>/', admin_views.lead_detail_view, name='lead_detail'),
    path('content/leads/<int:lead_id>/delete/', admin_views.lead_delete_view, name='lead_delete'),
    
    # NEWS MANAGEMENT
    path('content/news/', admin_views.news_list_view, name='news_list'),
    path('content/news/<int:news_id>/', admin_views.news_detail_view, name='news_detail'),
    path('content/news/add/', admin_views.news_create_view, name='news_create'),
    
    # PLACEMENTS MANAGEMENT
    path('content/placements/', admin_views.placements_list_view, name='placements_list'),
    path('content/placements/add/', admin_views.placement_create_view, name='placement_create'),
    
    # TESTIMONIALS MANAGEMENT
    path('content/testimonials/', admin_views.testimonials_list_view, name='testimonials_list'),
    path('content/testimonials/<int:testimonial_id>/', admin_views.testimonial_detail_view, name='testimonial_detail'),
    path('content/testimonials/<int:testimonial_id>/edit/', admin_views.testimonial_edit_view, name='testimonial_edit'),
    path('content/testimonials/<int:testimonial_id>/delete/', admin_views.testimonial_delete_view, name='testimonial_delete'),
    path('content/testimonials/add/', admin_views.testimonial_create_view, name='testimonial_create'),

    # LIVE SESSIONS
    path('live-sessions/', views.live_sessions_list_view, name='live_sessions_list'),
    path('live-sessions/add/', views.live_session_create_view, name='live_session_create'),
    path('live-sessions/<int:session_id>/', views.live_session_detail_view, name='live_session_detail'),
    path('live-sessions/<int:session_id>/edit/', views.live_session_edit_view, name='live_session_edit'),
    path('live-sessions/<int:session_id>/delete/', views.live_session_delete_view, name='live_session_delete'),
    path('live-sessions/<int:session_id>/participants/', views.session_manage_participants_view, name='session_manage_participants'),
    path('live-sessions/<int:session_id>/participants/<int:participant_id>/delete/', views.session_participant_delete_view, name='session_participant_delete'),
    path('live-sessions/<int:session_id>/start/', views.session_start_view, name='session_start'),
    path('live-sessions/<int:session_id>/end/', views.session_end_view, name='session_end'),
    path('live-sessions/<int:session_id>/cancel/', views.session_cancel_view, name='session_cancel'),
    path('live-sessions/<int:session_id>/announcements/add/', views.session_announcement_create_view, name='session_announcement_create'),

    # SYSTEM SETTINGS
    path('settings/', views.settings_list_view, name='settings_list'),
    path('settings/add/', views.setting_create_view, name='setting_create'),
    path('settings/<int:setting_id>/edit/', views.setting_edit_view, name='setting_edit'),
    path('settings/<int:setting_id>/delete/', views.setting_delete_view, name='setting_delete'),
    path('settings/<int:setting_id>/history/', views.setting_history_view, name='setting_history'),
    path('settings/<int:setting_id>/test-connection/', views.setting_test_connection_view, name='setting_test_connection'),

    # GOOGLE WORKSPACE OAUTH
    path('google/oauth/initiate/', views.google_oauth_initiate_view, name='google_oauth_initiate'),
    path('google/oauth/callback/', views.google_oauth_callback_view, name='google_oauth_callback'),
    path('google/oauth/disconnect/', views.google_oauth_disconnect_view, name='google_oauth_disconnect'),
    path('google/oauth/test/', views.google_oauth_test_view, name='google_oauth_test'),

    # AJAX ENDPOINTS
    path('get-course-info/<int:course_id>/', views.get_course_info, name='get_course_info'),
    path('get-enrollment-info/<int:enrollment_id>/', views.get_enrollment_info, name='get_enrollment_info'),
]