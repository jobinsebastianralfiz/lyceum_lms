from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import user_passes_test
from django.contrib.auth import authenticate, login, logout
from django.contrib import messages
from django.db.models import Count, Sum
from django.utils import timezone
from datetime import datetime, timedelta
from django.core.paginator import Paginator
from django.db.models import Q

from apps.users.models import User, Team
from apps.courses.models import Course, Module, VideoLesson, Category
from apps.payments.models import Enrollment, Payment, InstallmentPlan, TaxInvoice
from apps.youtube_integration.models import YouTubeVideo
from apps.notifications.models import Notification


def is_staff_user(user):
    return user.is_authenticated and user.is_staff


@user_passes_test(is_staff_user)
def dashboard_view(request):
    """Custom admin dashboard"""
    # COURSES Management Statistics
    total_categories = Category.objects.count()
    total_courses = Course.objects.count()
    total_modules = Module.objects.count()
    total_video_lessons = VideoLesson.objects.count()
    
    # PAYMENTS Management Statistics
    total_enrollments = Enrollment.objects.count()
    total_installment_plans = InstallmentPlan.objects.count()
    total_payments = Payment.objects.count()
    total_tax_invoices = TaxInvoice.objects.count()
    
    # USERS Management Statistics
    total_users = User.objects.filter(is_staff=False).count()
    total_teams = Team.objects.count()
    # For team memberships, we'll use a placeholder since model might not exist
    total_team_memberships = 0
    try:
        # Try to get team memberships through teams
        total_team_memberships = sum(team.team_memberships.count() if hasattr(team, 'team_memberships') else 0 for team in Team.objects.all())
    except:
        total_team_memberships = 0
    
    total_notifications = Notification.objects.count()
    
    # YOUTUBE Integration Statistics
    total_youtube_videos = YouTubeVideo.objects.count()
    
    # Revenue and Growth Statistics
    total_revenue = Payment.objects.filter(
        status='completed'
    ).aggregate(Sum('amount'))['amount__sum'] or 0
    
    active_enrollments = Enrollment.objects.filter(active=True).count()
    revenue_growth = 22  # Mock data for now
    
    # Quick stats for sidebar
    users_growth = 12  # +12%
    courses_growth = 8   # +8%
    enrollments_growth = 15  # +15%
    
    # Recent enrollments
    recent_enrollments = Enrollment.objects.select_related(
        'user', 'course', 'team'
    ).order_by('-enrolled_on')[:5]
    
    # Recent payments  
    recent_payments = Payment.objects.select_related(
        'enrollment__user'
    ).filter(status='completed').order_by('-created_at')[:5]
    
    context = {
        # COURSES Management
        'total_categories': total_categories,
        'total_courses': total_courses,
        'total_modules': total_modules,
        'total_video_lessons': total_video_lessons,
        
        # PAYMENTS Management
        'total_enrollments': total_enrollments,
        'total_installment_plans': total_installment_plans,
        'total_payments': total_payments,
        'total_tax_invoices': total_tax_invoices,
        
        # USERS Management
        'total_users': total_users,
        'total_teams': total_teams,
        'total_team_memberships': total_team_memberships,
        'total_notifications': total_notifications,
        
        # YOUTUBE Integration
        'total_youtube_videos': total_youtube_videos,
        
        # Revenue & Growth
        'total_revenue': total_revenue,
        'active_enrollments': active_enrollments,
        'revenue_growth': revenue_growth,
        'users_growth': users_growth,
        'courses_growth': courses_growth,
        'enrollments_growth': enrollments_growth,
        
        # Recent Activities
        'recent_enrollments': recent_enrollments,
        'recent_payments': recent_payments,
    }
    
    return render(request, 'custom_admin/dashboard.html', context)


@user_passes_test(is_staff_user)
def users_list_view(request):
    """List all users"""
    search_query = request.GET.get('search', '')
    users = User.objects.all()
    
    if search_query:
        users = users.filter(
            Q(name__icontains=search_query) |
            Q(email__icontains=search_query) |
            Q(username__icontains=search_query)
        )
    
    paginator = Paginator(users, 25)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'page_obj': page_obj,
        'search_query': search_query,
    }
    
    return render(request, 'custom_admin/users/list.html', context)


@user_passes_test(is_staff_user)
def user_detail_view(request, user_id):
    """View user details"""
    user = get_object_or_404(User, id=user_id)
    enrollments = Enrollment.objects.filter(user=user).select_related('course')
    
    context = {
        'user': user,
        'enrollments': enrollments,
    }
    
    return render(request, 'custom_admin/users/detail.html', context)


@user_passes_test(is_staff_user)
def courses_list_view(request):
    """List all courses"""
    search_query = request.GET.get('search', '')
    courses = Course.objects.annotate(
        enrollments_count=Count('enrollments')
    )
    
    if search_query:
        courses = courses.filter(
            Q(title__icontains=search_query) |
            Q(description__icontains=search_query)
        )
    
    paginator = Paginator(courses, 25)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'page_obj': page_obj,
        'search_query': search_query,
    }
    
    return render(request, 'custom_admin/courses/list.html', context)


@user_passes_test(is_staff_user)
def course_detail_view(request, course_id):
    """View course details"""
    course = get_object_or_404(Course, id=course_id)
    modules = Module.objects.filter(course=course).prefetch_related('video_lessons')
    enrollments = Enrollment.objects.filter(course=course).select_related('user', 'team')
    
    context = {
        'course': course,
        'modules': modules,
        'enrollments': enrollments,
    }
    
    return render(request, 'custom_admin/courses/detail.html', context)


@user_passes_test(is_staff_user)
def enrollments_list_view(request):
    """List all enrollments"""
    search_query = request.GET.get('search', '')
    enrollments = Enrollment.objects.select_related('user', 'course', 'team')
    
    if search_query:
        enrollments = enrollments.filter(
            Q(user__name__icontains=search_query) |
            Q(course__title__icontains=search_query) |
            Q(team__name__icontains=search_query)
        )
    
    paginator = Paginator(enrollments, 25)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'page_obj': page_obj,
        'search_query': search_query,
    }
    
    return render(request, 'custom_admin/enrollments/list.html', context)


@user_passes_test(is_staff_user)
def payments_list_view(request):
    """List all payments"""
    search_query = request.GET.get('search', '')
    payments = Payment.objects.select_related('enrollment__user', 'enrollment__course')
    
    if search_query:
        payments = payments.filter(
            Q(enrollment__user__name__icontains=search_query) |
            Q(enrollment__course__title__icontains=search_query)
        )
    
    paginator = Paginator(payments, 25)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'page_obj': page_obj,
        'search_query': search_query,
    }
    
    return render(request, 'custom_admin/payments/list.html', context)


@user_passes_test(is_staff_user)
def teams_list_view(request):
    """List all teams"""
    search_query = request.GET.get('search', '')
    teams = Team.objects.annotate(
        members_count=Count('team_memberships')
    )
    
    if search_query:
        teams = teams.filter(name__icontains=search_query)
    
    paginator = Paginator(teams, 25) 
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'page_obj': page_obj,
        'search_query': search_query,
    }
    
    return render(request, 'custom_admin/teams/list.html', context)


def login_view(request):
    """Custom admin login"""
    if request.user.is_authenticated and request.user.is_staff:
        return redirect('custom_admin:dashboard')
    
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        
        user = authenticate(request, username=username, password=password)
        if user is not None and user.is_staff:
            login(request, user)
            return redirect('custom_admin:dashboard')
        else:
            messages.error(request, 'Invalid credentials or insufficient permissions.')
    
    return render(request, 'custom_admin/login.html')


@user_passes_test(is_staff_user)
def logout_view(request):
    """Custom admin logout"""
    logout(request)
    return redirect('custom_admin:login')


# ==============================================================================
# CATEGORIES VIEWS
# ==============================================================================

@user_passes_test(is_staff_user)
def categories_list_view(request):
    """List all categories"""
    search_query = request.GET.get('search', '')
    categories = Category.objects.all()
    
    if search_query:
        categories = categories.filter(name__icontains=search_query)
    
    paginator = Paginator(categories, 25)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'page_obj': page_obj,
        'search_query': search_query,
    }
    
    return render(request, 'custom_admin/categories/list.html', context)

@user_passes_test(is_staff_user)
def category_create_view(request):
    """Create a new category"""
    return render(request, 'custom_admin/categories/form.html', {
        'title': 'Add Category',
        'is_edit': False
    })

@user_passes_test(is_staff_user)
def category_edit_view(request, category_id):
    """Edit a category"""
    category = get_object_or_404(Category, id=category_id)
    return render(request, 'custom_admin/categories/form.html', {
        'category': category,
        'title': 'Edit Category',
        'is_edit': True
    })

@user_passes_test(is_staff_user)
def category_delete_view(request, category_id):
    """Delete a category"""
    category = get_object_or_404(Category, id=category_id)
    if request.method == 'POST':
        category.delete()
        messages.success(request, f'Category "{category.name}" deleted successfully.')
        return redirect('custom_admin:categories_list')
    return render(request, 'custom_admin/categories/delete.html', {'category': category})


# ==============================================================================
# COURSE CRUD VIEWS
# ==============================================================================

@user_passes_test(is_staff_user)
def course_create_view(request):
    """Create a new course"""
    return render(request, 'custom_admin/courses/form.html', {
        'title': 'Add Course',
        'is_edit': False
    })

@user_passes_test(is_staff_user)
def course_edit_view(request, course_id):
    """Edit a course"""
    course = get_object_or_404(Course, id=course_id)
    return render(request, 'custom_admin/courses/form.html', {
        'course': course,
        'title': 'Edit Course',
        'is_edit': True
    })

@user_passes_test(is_staff_user)
def course_delete_view(request, course_id):
    """Delete a course"""
    course = get_object_or_404(Course, id=course_id)
    if request.method == 'POST':
        course.delete()
        messages.success(request, f'Course "{course.title}" deleted successfully.')
        return redirect('custom_admin:courses_list')
    return render(request, 'custom_admin/courses/delete.html', {'course': course})


# ==============================================================================
# MODULES VIEWS
# ==============================================================================

@user_passes_test(is_staff_user)
def modules_list_view(request):
    """List all modules"""
    search_query = request.GET.get('search', '')
    modules = Module.objects.select_related('course')
    
    if search_query:
        modules = modules.filter(
            Q(title__icontains=search_query) |
            Q(course__title__icontains=search_query)
        )
    
    paginator = Paginator(modules, 25)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'page_obj': page_obj,
        'search_query': search_query,
    }
    
    return render(request, 'custom_admin/modules/list.html', context)

@user_passes_test(is_staff_user)
def module_create_view(request):
    """Create a new module"""
    return render(request, 'custom_admin/modules/form.html', {
        'title': 'Add Module',
        'is_edit': False
    })

@user_passes_test(is_staff_user)
def module_edit_view(request, module_id):
    """Edit a module"""
    module = get_object_or_404(Module, id=module_id)
    return render(request, 'custom_admin/modules/form.html', {
        'module': module,
        'title': 'Edit Module',
        'is_edit': True
    })

@user_passes_test(is_staff_user)
def module_delete_view(request, module_id):
    """Delete a module"""
    module = get_object_or_404(Module, id=module_id)
    if request.method == 'POST':
        module.delete()
        messages.success(request, f'Module "{module.title}" deleted successfully.')
        return redirect('custom_admin:modules_list')
    return render(request, 'custom_admin/modules/delete.html', {'module': module})


# ==============================================================================
# STUDENT PROGRESS VIEWS
# ==============================================================================

@user_passes_test(is_staff_user)
def student_progress_list_view(request):
    """List student progress"""
    # For now, show enrollments as progress indicator
    return redirect('custom_admin:enrollments_list')


# ==============================================================================
# VIDEO LESSONS VIEWS
# ==============================================================================

@user_passes_test(is_staff_user)
def video_lessons_list_view(request):
    """List all video lessons"""
    search_query = request.GET.get('search', '')
    lessons = VideoLesson.objects.select_related('module', 'module__course')
    
    if search_query:
        lessons = lessons.filter(
            Q(title__icontains=search_query) |
            Q(module__title__icontains=search_query) |
            Q(module__course__title__icontains=search_query)
        )
    
    paginator = Paginator(lessons, 25)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'page_obj': page_obj,
        'search_query': search_query,
    }
    
    return render(request, 'custom_admin/video_lessons/list.html', context)

@user_passes_test(is_staff_user)
def video_lesson_create_view(request):
    """Create a new video lesson"""
    return render(request, 'custom_admin/video_lessons/form.html', {
        'title': 'Add Video Lesson',
        'is_edit': False
    })

@user_passes_test(is_staff_user)
def video_lesson_edit_view(request, lesson_id):
    """Edit a video lesson"""
    lesson = get_object_or_404(VideoLesson, id=lesson_id)
    return render(request, 'custom_admin/video_lessons/form.html', {
        'lesson': lesson,
        'title': 'Edit Video Lesson',
        'is_edit': True
    })

@user_passes_test(is_staff_user)
def video_lesson_delete_view(request, lesson_id):
    """Delete a video lesson"""
    lesson = get_object_or_404(VideoLesson, id=lesson_id)
    if request.method == 'POST':
        lesson.delete()
        messages.success(request, f'Video lesson "{lesson.title}" deleted successfully.')
        return redirect('custom_admin:video_lessons_list')
    return render(request, 'custom_admin/video_lessons/delete.html', {'lesson': lesson})


# ==============================================================================
# NOTIFICATIONS VIEWS
# ==============================================================================

@user_passes_test(is_staff_user)
def email_templates_list_view(request):
    """List email templates"""
    # Placeholder - implement when EmailTemplate model exists
    return render(request, 'custom_admin/email_templates/list.html', {
        'page_obj': None,
        'search_query': ''
    })

@user_passes_test(is_staff_user)
def email_template_create_view(request):
    """Create email template"""
    return render(request, 'custom_admin/email_templates/form.html', {
        'title': 'Add Email Template',
        'is_edit': False
    })

@user_passes_test(is_staff_user)
def email_template_edit_view(request, template_id):
    """Edit email template"""
    return render(request, 'custom_admin/email_templates/form.html', {
        'title': 'Edit Email Template',
        'is_edit': True
    })

@user_passes_test(is_staff_user)
def email_template_delete_view(request, template_id):
    """Delete email template"""
    return redirect('custom_admin:email_templates_list')

@user_passes_test(is_staff_user)
def notifications_list_view(request):
    """List notifications"""
    search_query = request.GET.get('search', '')
    notifications = Notification.objects.select_related('user')
    
    if search_query:
        notifications = notifications.filter(
            Q(title__icontains=search_query) |
            Q(user__name__icontains=search_query)
        )
    
    paginator = Paginator(notifications, 25)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'page_obj': page_obj,
        'search_query': search_query,
    }
    
    return render(request, 'custom_admin/notifications/list.html', context)

@user_passes_test(is_staff_user)
def notification_create_view(request):
    """Create notification"""
    return render(request, 'custom_admin/notifications/form.html', {
        'title': 'Add Notification',
        'is_edit': False
    })

@user_passes_test(is_staff_user)
def notification_edit_view(request, notification_id):
    """Edit notification"""
    notification = get_object_or_404(Notification, id=notification_id)
    return render(request, 'custom_admin/notifications/form.html', {
        'notification': notification,
        'title': 'Edit Notification',
        'is_edit': True
    })

@user_passes_test(is_staff_user)
def notification_delete_view(request, notification_id):
    """Delete notification"""
    notification = get_object_or_404(Notification, id=notification_id)
    if request.method == 'POST':
        notification.delete()
        messages.success(request, f'Notification deleted successfully.')
        return redirect('custom_admin:notifications_list')
    return render(request, 'custom_admin/notifications/delete.html', {'notification': notification})


# ==============================================================================
# PAYMENT CRUD VIEWS
# ==============================================================================

@user_passes_test(is_staff_user)
def enrollment_create_view(request):
    """Create enrollment"""
    return render(request, 'custom_admin/enrollments/form.html', {
        'title': 'Add Enrollment',
        'is_edit': False
    })

@user_passes_test(is_staff_user)
def enrollment_edit_view(request, enrollment_id):
    """Edit enrollment"""
    enrollment = get_object_or_404(Enrollment, id=enrollment_id)
    return render(request, 'custom_admin/enrollments/form.html', {
        'enrollment': enrollment,
        'title': 'Edit Enrollment',
        'is_edit': True
    })

@user_passes_test(is_staff_user)
def enrollment_delete_view(request, enrollment_id):
    """Delete enrollment"""
    enrollment = get_object_or_404(Enrollment, id=enrollment_id)
    if request.method == 'POST':
        enrollment.delete()
        messages.success(request, f'Enrollment deleted successfully.')
        return redirect('custom_admin:enrollments_list')
    return render(request, 'custom_admin/enrollments/delete.html', {'enrollment': enrollment})

@user_passes_test(is_staff_user)
def installment_plans_list_view(request):
    """List installment plans"""
    search_query = request.GET.get('search', '')
    plans = InstallmentPlan.objects.select_related('enrollment', 'enrollment__user', 'enrollment__course')
    
    if search_query:
        plans = plans.filter(
            Q(enrollment__user__name__icontains=search_query) |
            Q(enrollment__course__title__icontains=search_query)
        )
    
    paginator = Paginator(plans, 25)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'page_obj': page_obj,
        'search_query': search_query,
    }
    
    return render(request, 'custom_admin/installment_plans/list.html', context)

@user_passes_test(is_staff_user)
def installment_plan_create_view(request):
    """Create installment plan"""
    return render(request, 'custom_admin/installment_plans/form.html', {
        'title': 'Add Installment Plan',
        'is_edit': False
    })

@user_passes_test(is_staff_user)
def installment_plan_edit_view(request, plan_id):
    """Edit installment plan"""
    plan = get_object_or_404(InstallmentPlan, id=plan_id)
    return render(request, 'custom_admin/installment_plans/form.html', {
        'plan': plan,
        'title': 'Edit Installment Plan',
        'is_edit': True
    })

@user_passes_test(is_staff_user)
def installment_plan_delete_view(request, plan_id):
    """Delete installment plan"""
    plan = get_object_or_404(InstallmentPlan, id=plan_id)
    if request.method == 'POST':
        plan.delete()
        messages.success(request, f'Installment plan deleted successfully.')
        return redirect('custom_admin:installment_plans_list')
    return render(request, 'custom_admin/installment_plans/delete.html', {'plan': plan})

@user_passes_test(is_staff_user)
def payment_create_view(request):
    """Create payment"""
    return render(request, 'custom_admin/payments/form.html', {
        'title': 'Add Payment',
        'is_edit': False
    })

@user_passes_test(is_staff_user)
def payment_edit_view(request, payment_id):
    """Edit payment"""
    payment = get_object_or_404(Payment, id=payment_id)
    return render(request, 'custom_admin/payments/form.html', {
        'payment': payment,
        'title': 'Edit Payment',
        'is_edit': True
    })

@user_passes_test(is_staff_user)
def payment_delete_view(request, payment_id):
    """Delete payment"""
    payment = get_object_or_404(Payment, id=payment_id)
    if request.method == 'POST':
        payment.delete()
        messages.success(request, f'Payment deleted successfully.')
        return redirect('custom_admin:payments_list')
    return render(request, 'custom_admin/payments/delete.html', {'payment': payment})

@user_passes_test(is_staff_user)
def tax_invoices_list_view(request):
    """List tax invoices"""
    search_query = request.GET.get('search', '')
    invoices = TaxInvoice.objects.select_related('enrollment', 'enrollment__user', 'payment')
    
    if search_query:
        invoices = invoices.filter(
            Q(invoice_number__icontains=search_query) |
            Q(enrollment__user__name__icontains=search_query)
        )
    
    paginator = Paginator(invoices, 25)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'page_obj': page_obj,
        'search_query': search_query,
    }
    
    return render(request, 'custom_admin/tax_invoices/list.html', context)

@user_passes_test(is_staff_user)
def tax_invoice_create_view(request):
    """Create tax invoice"""
    return render(request, 'custom_admin/tax_invoices/form.html', {
        'title': 'Add Tax Invoice',
        'is_edit': False
    })

@user_passes_test(is_staff_user)
def tax_invoice_edit_view(request, invoice_id):
    """Edit tax invoice"""
    invoice = get_object_or_404(TaxInvoice, id=invoice_id)
    return render(request, 'custom_admin/tax_invoices/form.html', {
        'invoice': invoice,
        'title': 'Edit Tax Invoice',
        'is_edit': True
    })

@user_passes_test(is_staff_user)
def tax_invoice_delete_view(request, invoice_id):
    """Delete tax invoice"""
    invoice = get_object_or_404(TaxInvoice, id=invoice_id)
    if request.method == 'POST':
        invoice.delete()
        messages.success(request, f'Tax invoice deleted successfully.')
        return redirect('custom_admin:tax_invoices_list')
    return render(request, 'custom_admin/tax_invoices/delete.html', {'invoice': invoice})


# ==============================================================================
# TEAM/USER CRUD VIEWS
# ==============================================================================

@user_passes_test(is_staff_user)
def team_memberships_list_view(request):
    """List team memberships"""
    # For now redirect to teams list
    return redirect('custom_admin:teams_list')

@user_passes_test(is_staff_user)
def team_membership_create_view(request):
    """Create team membership"""
    return render(request, 'custom_admin/team_memberships/form.html', {
        'title': 'Add Team Membership',
        'is_edit': False
    })

@user_passes_test(is_staff_user)
def team_membership_edit_view(request, membership_id):
    """Edit team membership"""
    return render(request, 'custom_admin/team_memberships/form.html', {
        'title': 'Edit Team Membership',
        'is_edit': True
    })

@user_passes_test(is_staff_user)
def team_membership_delete_view(request, membership_id):
    """Delete team membership"""
    return redirect('custom_admin:team_memberships_list')

@user_passes_test(is_staff_user)
def team_create_view(request):
    """Create team"""
    return render(request, 'custom_admin/teams/form.html', {
        'title': 'Add Team',
        'is_edit': False
    })

@user_passes_test(is_staff_user)
def team_edit_view(request, team_id):
    """Edit team"""
    team = get_object_or_404(Team, id=team_id)
    return render(request, 'custom_admin/teams/form.html', {
        'team': team,
        'title': 'Edit Team',
        'is_edit': True
    })

@user_passes_test(is_staff_user)
def team_delete_view(request, team_id):
    """Delete team"""
    team = get_object_or_404(Team, id=team_id)
    if request.method == 'POST':
        team.delete()
        messages.success(request, f'Team "{team.name}" deleted successfully.')
        return redirect('custom_admin:teams_list')
    return render(request, 'custom_admin/teams/delete.html', {'team': team})

@user_passes_test(is_staff_user)
def user_create_view(request):
    """Create user"""
    return render(request, 'custom_admin/users/form.html', {
        'title': 'Add User',
        'is_edit': False
    })

@user_passes_test(is_staff_user)
def user_edit_view(request, user_id):
    """Edit user"""
    user = get_object_or_404(User, id=user_id)
    return render(request, 'custom_admin/users/form.html', {
        'user': user,
        'title': 'Edit User',
        'is_edit': True
    })

@user_passes_test(is_staff_user)
def user_delete_view(request, user_id):
    """Delete user"""
    user = get_object_or_404(User, id=user_id)
    if request.method == 'POST':
        user.delete()
        messages.success(request, f'User "{user.get_full_name() or user.username}" deleted successfully.')
        return redirect('custom_admin:users_list')
    return render(request, 'custom_admin/users/delete.html', {'user': user})


# ==============================================================================
# YOUTUBE INTEGRATION VIEWS
# ==============================================================================

@user_passes_test(is_staff_user)
def youtube_channel_configs_list_view(request):
    """List YouTube channel configs"""
    # Placeholder - implement when YouTubeChannelConfig model exists
    return render(request, 'custom_admin/youtube_channel_configs/list.html', {
        'page_obj': None,
        'search_query': ''
    })

@user_passes_test(is_staff_user)
def youtube_channel_config_create_view(request):
    """Create YouTube channel config"""
    return render(request, 'custom_admin/youtube_channel_configs/form.html', {
        'title': 'Add YouTube Channel Config',
        'is_edit': False
    })

@user_passes_test(is_staff_user)
def youtube_channel_config_edit_view(request, config_id):
    """Edit YouTube channel config"""
    return render(request, 'custom_admin/youtube_channel_configs/form.html', {
        'title': 'Edit YouTube Channel Config',
        'is_edit': True
    })

@user_passes_test(is_staff_user)
def youtube_channel_config_delete_view(request, config_id):
    """Delete YouTube channel config"""
    return redirect('custom_admin:youtube_channel_configs_list')

@user_passes_test(is_staff_user)
def youtube_videos_list_view(request):
    """List YouTube videos"""
    search_query = request.GET.get('search', '')
    videos = YouTubeVideo.objects.all()
    
    if search_query:
        videos = videos.filter(
            Q(title__icontains=search_query) |
            Q(channel_title__icontains=search_query)
        )
    
    paginator = Paginator(videos, 25)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'page_obj': page_obj,
        'search_query': search_query,
    }
    
    return render(request, 'custom_admin/youtube_videos/list.html', context)

@user_passes_test(is_staff_user)
def youtube_video_create_view(request):
    """Create YouTube video"""
    return render(request, 'custom_admin/youtube_videos/form.html', {
        'title': 'Add YouTube Video',
        'is_edit': False
    })

@user_passes_test(is_staff_user)
def youtube_video_edit_view(request, video_id):
    """Edit YouTube video"""
    video = get_object_or_404(YouTubeVideo, id=video_id)
    return render(request, 'custom_admin/youtube_videos/form.html', {
        'video': video,
        'title': 'Edit YouTube Video',
        'is_edit': True
    })

@user_passes_test(is_staff_user)
def youtube_video_delete_view(request, video_id):
    """Delete YouTube video"""
    video = get_object_or_404(YouTubeVideo, id=video_id)
    if request.method == 'POST':
        video.delete()
        messages.success(request, f'YouTube video "{video.title}" deleted successfully.')
        return redirect('custom_admin:youtube_videos_list')
    return render(request, 'custom_admin/youtube_videos/delete.html', {'video': video})