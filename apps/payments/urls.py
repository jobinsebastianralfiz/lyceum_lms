from django.urls import path
from . import views

app_name = 'payments'

urlpatterns = [
    # Course pricing and purchase
    path('course/<int:course_id>/pricing/', views.CoursePricingPreviewView.as_view(), name='course-pricing'),
    path('purchase-course/', views.CourseEnrollmentView.as_view(), name='purchase-course'),
    
    # Student enrollment and payment history
    path('my-enrollments/', views.UserEnrollmentsView.as_view(), name='my-enrollments'),
    path('enrollments/<int:enrollment_id>/payments/', views.EnrollmentPaymentHistoryView.as_view(), name='enrollment-payment-history'),
    path('enrollments/<int:enrollment_id>/installment-plan/', views.EnrollmentInstallmentPlanView.as_view(), name='enrollment-installment-plan'),
]