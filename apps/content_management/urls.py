from django.urls import path
from . import views

app_name = 'content_management'

urlpatterns = [
    # Mobile App APIs

    # Lead Management
    path('leads/submit/', views.LeadCreateView.as_view(), name='lead-create'),
    path('leads/my-leads/', views.MyLeadStatusListView.as_view(), name='my-leads'),
    path('leads/my-leads/<int:pk>/', views.MyLeadStatusDetailView.as_view(), name='my-lead-detail'),

    # News APIs
    path('news/', views.NewsListView.as_view(), name='news-list'),
    path('news/<slug:slug>/', views.NewsDetailView.as_view(), name='news-detail'),

    # Placement APIs
    path('placements/', views.PlacementListView.as_view(), name='placement-list'),
    path('placements/<int:pk>/', views.PlacementDetailView.as_view(), name='placement-detail'),

    # Testimonial APIs
    path('testimonials/', views.TestimonialListView.as_view(), name='testimonial-list'),
    path('testimonials/<int:pk>/', views.TestimonialDetailView.as_view(), name='testimonial-detail'),
    path('testimonials/<int:pk>/like/', views.TestimonialLikeView.as_view(), name='testimonial-like'),

    # Event APIs (NEW)
    path('events/', views.EventListView.as_view(), name='event-list'),
    path('events/<slug:slug>/', views.EventDetailView.as_view(), name='event-detail'),

    # Achievement APIs (NEW)
    path('achievements/', views.AchievementListView.as_view(), name='achievement-list'),
    path('achievements/<int:pk>/', views.AchievementDetailView.as_view(), name='achievement-detail'),

    # Banner APIs (NEW)
    path('banners/', views.BannerListView.as_view(), name='banner-list'),

    # Course Enquiry APIs (NEW)
    path('course-enquiry/submit/', views.CourseEnquiryCreateView.as_view(), name='course-enquiry-create'),
    path('course-enquiry/my-enquiries/', views.MyCourseEnquiriesView.as_view(), name='my-course-enquiries'),

    # Dashboard Content
    path('dashboard/', views.DashboardContentView.as_view(), name='dashboard-content'),
    path('dashboard/enhanced/', views.EnhancedDashboardView.as_view(), name='enhanced-dashboard'),

    # Admin APIs (for custom admin panel)
    path('admin/leads/', views.AdminLeadListView.as_view(), name='admin-lead-list'),
    path('admin/leads/<int:pk>/', views.AdminLeadDetailView.as_view(), name='admin-lead-detail'),
    path('admin/stats/', views.ContentStatsView.as_view(), name='admin-stats'),
]