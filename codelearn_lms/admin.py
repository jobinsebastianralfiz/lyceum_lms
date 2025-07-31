from django.contrib import admin
from django.db.models import Sum, Count
from django.utils import timezone
from datetime import datetime, timedelta
from django.contrib.admin import AdminSite
from django.template.response import TemplateResponse

from apps.users.models import User, Team
from apps.courses.models import Course
from apps.payments.models import Enrollment, Payment
from apps.youtube_integration.models import YouTubeVideo

class CodeLearnAdminSite(AdminSite):
    site_header = 'CodeLearn LMS Administration'
    site_title = 'CodeLearn LMS Admin'
    index_title = 'Welcome to CodeLearn LMS Administration'
    
    def index(self, request, extra_context=None):
        extra_context = extra_context or {}
        
        # Dashboard statistics
        now = timezone.now()
        current_month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        
        # Basic counts
        extra_context['total_students'] = User.objects.filter(role='student').count()
        extra_context['total_courses'] = Course.objects.filter(is_published=True).count()
        extra_context['total_enrollments'] = Enrollment.objects.filter(active=True).count()
        extra_context['youtube_videos'] = YouTubeVideo.objects.filter(is_available=True).count()
        
        # Financial data
        monthly_payments = Payment.objects.filter(
            status='completed',
            payment_date__gte=current_month_start
        ).aggregate(total=Sum('amount'))
        extra_context['monthly_revenue'] = monthly_payments['total'] or 0
        
        extra_context['pending_payments'] = Payment.objects.filter(status='pending').count()
        
        # Team statistics
        extra_context['total_teams'] = Team.objects.filter(is_active=True).count()
        extra_context['active_team_members'] = Team.objects.filter(is_active=True).aggregate(
            total_members=Sum('memberships__id')
        )['total_members'] or 0
        
        # Recent data
        extra_context['recent_enrollments'] = Enrollment.objects.select_related(
            'user', 'course', 'team'
        ).order_by('-enrolled_on')[:5]
        
        extra_context['recent_payments'] = Payment.objects.select_related(
            'enrollment__user'
        ).filter(status='completed').order_by('-payment_date')[:5]
        
        return super().index(request, extra_context)

# Create custom admin site instance
admin_site = CodeLearnAdminSite(name='codelearn_admin')

# Register all models with the custom admin site
from apps.users.admin import UserAdmin, TeamAdmin, TeamMembershipAdmin
from apps.courses.admin import CategoryAdmin, CourseAdmin, ModuleAdmin, VideoLessonAdmin, StudentProgressAdmin
from apps.payments.admin import EnrollmentAdmin, InstallmentPlanAdmin, PaymentAdmin, TaxInvoiceAdmin
from apps.notifications.admin import NotificationAdmin, EmailTemplateAdmin
from apps.youtube_integration.admin import YouTubeChannelConfigAdmin, YouTubeVideoAdmin

from apps.users.models import User, Team, TeamMembership
from apps.courses.models import Category, Course, Module, VideoLesson, StudentProgress
from apps.payments.models import Enrollment, InstallmentPlan, Payment, TaxInvoice
from apps.notifications.models import Notification, EmailTemplate
from apps.youtube_integration.models import YouTubeChannelConfig, YouTubeVideo

# Register models with custom admin site
admin_site.register(User, UserAdmin)
admin_site.register(Team, TeamAdmin)
admin_site.register(TeamMembership, TeamMembershipAdmin)
admin_site.register(Category, CategoryAdmin)
admin_site.register(Course, CourseAdmin)
admin_site.register(Module, ModuleAdmin)
admin_site.register(VideoLesson, VideoLessonAdmin)
admin_site.register(StudentProgress, StudentProgressAdmin)
admin_site.register(Enrollment, EnrollmentAdmin)
admin_site.register(InstallmentPlan, InstallmentPlanAdmin)
admin_site.register(Payment, PaymentAdmin)
admin_site.register(TaxInvoice, TaxInvoiceAdmin)
admin_site.register(Notification, NotificationAdmin)
admin_site.register(EmailTemplate, EmailTemplateAdmin)
admin_site.register(YouTubeChannelConfig, YouTubeChannelConfigAdmin)
admin_site.register(YouTubeVideo, YouTubeVideoAdmin)