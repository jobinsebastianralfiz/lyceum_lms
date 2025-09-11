import json
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import user_passes_test
from django.contrib.auth import authenticate, login, logout
from django.contrib import messages
from django.db.models import Count, Sum
from django.utils import timezone
from datetime import datetime, timedelta
from django.core.paginator import Paginator
from django.db.models import Q
from django.urls import reverse
from django.http import JsonResponse

from apps.users.models import User, Team, TeamMembership
from apps.courses.models import (
    Course, Module, VideoLesson, Category,
    Assignment, Quiz, QuizQuestion, QuizChoice, AssignmentSubmission,
    QuizAttempt, QuizAnswer, ModuleProgress, StudentAnalytics, ProgressAlert, MentorSession
)
from apps.payments.models import Enrollment, Payment, InstallmentPlan, TaxInvoice
from apps.youtube_integration.models import YouTubeVideo, YouTubeChannelConfig
from apps.notifications.models import Notification
from apps.ratings.models import CourseRating, CourseReview, ReviewHelpful
from .forms import CustomVideoLessonForm, CustomAssignmentForm, CustomQuizQuestionForm, CustomQuizChoiceForm, CustomQuizQuestionWithChoicesForm
from .quiz_reset_views import quiz_attempt_reset_view, quiz_attempt_delete_view


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
    total_assignments = Assignment.objects.count()
    total_quizzes = Quiz.objects.count()
    total_quiz_questions = QuizQuestion.objects.count()
    
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
        total_team_memberships = sum(team.memberships.count() if hasattr(team, 'memberships') else 0 for team in Team.objects.all())
    except:
        total_team_memberships = 0
    
    total_notifications = Notification.objects.count()
    
    # YOUTUBE Integration Statistics
    total_youtube_videos = YouTubeVideo.objects.count()
    
    # Revenue and Growth Statistics
    total_revenue = Payment.objects.filter(
        status='completed'
    ).aggregate(Sum('amount'))['amount__sum'] or 0
    
    # Calculate pending income from outstanding enrollment amounts
    pending_income = 0
    for enrollment in Enrollment.objects.filter(payment_status__in=['pending', 'partial']):
        pending_income += enrollment.outstanding_amount
    
    active_enrollments = Enrollment.objects.filter(active=True).count()
    revenue_growth = 22  # Mock data for now
    
    # Chart data for enrollment overview
    import calendar
    
    # Get the last 6 months of data
    current_date = timezone.now()
    months_data = []
    enrollments_data = []
    revenue_data = []
    
    for i in range(5, -1, -1):
        month_date = current_date - timedelta(days=30*i)
        month_start = month_date.replace(day=1)
        if i == 0:
            month_end = current_date
        else:
            next_month = month_start.replace(month=month_start.month % 12 + 1) if month_start.month < 12 else month_start.replace(year=month_start.year + 1, month=1)
            month_end = next_month - timedelta(days=1)
        
        month_name = calendar.month_abbr[month_date.month]
        months_data.append(month_name)
        
        # Count enrollments for this month
        monthly_enrollments = Enrollment.objects.filter(
            enrolled_on__gte=month_start,
            enrolled_on__lte=month_end
        ).count()
        enrollments_data.append(monthly_enrollments)
        
        # Calculate revenue for this month
        monthly_revenue = Payment.objects.filter(
            status='completed',
            payment_date__gte=month_start,
            payment_date__lte=month_end
        ).aggregate(Sum('amount'))['amount__sum'] or 0
        revenue_data.append(float(monthly_revenue))
    
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
    
    # MENTORING & ANALYTICS Statistics
    high_risk_students = StudentAnalytics.objects.filter(
        risk_level__in=['critical', 'high']
    ).count()
    
    inactive_students = User.objects.filter(
        role='student',
        last_login__lt=timezone.now() - timedelta(days=7)
    ).count()
    
    mentor_sessions = MentorSession.objects.count()
    
    active_alerts = ProgressAlert.objects.filter(
        is_resolved=False
    ).count()
    
    context = {
        # COURSES Management
        'total_categories': total_categories,
        'total_courses': total_courses,
        'total_modules': total_modules,
        'total_video_lessons': total_video_lessons,
        'total_assignments': total_assignments,
        'total_quizzes': total_quizzes,
        'total_quiz_questions': total_quiz_questions,
        
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
        'pending_income': pending_income,
        'active_enrollments': active_enrollments,
        'revenue_growth': revenue_growth,
        'users_growth': users_growth,
        'courses_growth': courses_growth,
        'enrollments_growth': enrollments_growth,
        
        # Chart data (JSON-ready)
        'chart_months': json.dumps(months_data),
        'chart_enrollments': json.dumps(enrollments_data),
        'chart_revenue': json.dumps(revenue_data),
        
        # MENTORING & ANALYTICS
        'high_risk_students': high_risk_students,
        'inactive_students': inactive_students,
        'mentor_sessions': mentor_sessions,
        'active_alerts': active_alerts,
        
        # Recent Activities
        'recent_enrollments': recent_enrollments,
        'recent_payments': recent_payments,
    }
    
    return render(request, 'custom_admin/dashboard.html', context)


@user_passes_test(is_staff_user)
def users_list_view(request):
    """List all users"""
    search_query = request.GET.get('search', '')
    users = User.objects.all().order_by('username')
    
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
    ).order_by('title')
    
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
    modules = Module.objects.filter(course=course).prefetch_related(
        'video_lessons', 'assignments', 'quizzes'
    ).order_by('order')
    enrollments = Enrollment.objects.filter(course=course).select_related('user', 'team')
    
    # Add assignments and quizzes count for each module
    for module in modules:
        module.assignments_count = module.assignments.count()
        module.quizzes_count = module.quizzes.count()
    
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
    enrollments = Enrollment.objects.select_related('user', 'course', 'team').order_by('-created_at')
    
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
    payments = Payment.objects.select_related('enrollment__user', 'enrollment__course').order_by('-created_at')
    
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
        members_count=Count('memberships')
    ).order_by('name')
    
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
    categories = Category.objects.all().order_by('name')
    
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
    if request.method == 'POST':
        try:
            name = request.POST.get('name')
            description = request.POST.get('description', '')
            
            if not name:
                messages.error(request, 'Category name is required.')
                return render(request, 'custom_admin/categories/form.html', {
                    'title': 'Add Category',
                    'is_edit': False
                })
            
            # Create the category
            category = Category.objects.create(
                name=name,
                description=description
            )
            
            messages.success(request, f'Category "{category.name}" created successfully.')
            return redirect('custom_admin:categories_list')
            
        except Exception as e:
            messages.error(request, f'Error creating category: {str(e)}')
            return render(request, 'custom_admin/categories/form.html', {
                'title': 'Add Category',
                'is_edit': False
            })
    
    return render(request, 'custom_admin/categories/form.html', {
        'title': 'Add Category',
        'is_edit': False
    })

@user_passes_test(is_staff_user)
def category_edit_view(request, category_id):
    """Edit a category"""
    category = get_object_or_404(Category, id=category_id)
    
    if request.method == 'POST':
        try:
            name = request.POST.get('name')
            description = request.POST.get('description', '')
            
            if not name:
                messages.error(request, 'Category name is required.')
                return render(request, 'custom_admin/categories/form.html', {
                    'category': category,
                    'title': 'Edit Category',
                    'is_edit': True
                })
            
            # Update the category
            category.name = name
            category.description = description
            category.save()
            
            messages.success(request, f'Category "{category.name}" updated successfully.')
            return redirect('custom_admin:categories_list')
            
        except Exception as e:
            messages.error(request, f'Error updating category: {str(e)}')
            return render(request, 'custom_admin/categories/form.html', {
                'category': category,
                'title': 'Edit Category',
                'is_edit': True
            })
    
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
    categories = Category.objects.all()
    
    if request.method == 'POST':
        try:
            # Get form data
            title = request.POST.get('title')
            description = request.POST.get('description')
            curriculum = request.POST.get('curriculum', '')
            what_you_will_learn = request.POST.get('what_you_will_learn', '')
            category_id = request.POST.get('category')
            price = request.POST.get('price', '0.00')
            is_free = request.POST.get('is_free') == 'on'
            preview_video = request.POST.get('preview_video')
            is_published = request.POST.get('is_published') == 'on'
            allow_public_enrollment = request.POST.get('allow_public_enrollment') == 'on'
            
            # Validate required fields
            if not all([title, description, category_id]):
                messages.error(request, 'Please fill in all required fields.')
                return render(request, 'custom_admin/courses/form.html', {
                    'title': 'Add Course',
                    'is_edit': False,
                    'categories': categories
                })
            
            # Get category
            category = get_object_or_404(Category, id=category_id)
            
            # Handle file upload
            thumbnail = request.FILES.get('thumbnail')
            
            # Create course
            course = Course.objects.create(
                title=title,
                description=description,
                curriculum=curriculum,
                what_you_will_learn=what_you_will_learn,
                category=category,
                price=float(price) if price else 0.00,
                is_free=is_free,
                thumbnail=thumbnail,
                preview_video=preview_video,
                is_published=is_published,
                allow_public_enrollment=allow_public_enrollment,
                created_by=request.user
            )
            
            messages.success(request, f'Course "{course.title}" created successfully.')
            return redirect('custom_admin:course_detail', course_id=course.id)
            
        except Exception as e:
            messages.error(request, f'Error creating course: {str(e)}')
    
    return render(request, 'custom_admin/courses/form.html', {
        'title': 'Add Course',
        'is_edit': False,
        'categories': categories
    })

@user_passes_test(is_staff_user)
def course_edit_view(request, course_id):
    """Edit a course"""
    course = get_object_or_404(Course, id=course_id)
    categories = Category.objects.all()
    
    if request.method == 'POST':
        try:
            # Get form data
            title = request.POST.get('title')
            description = request.POST.get('description')
            curriculum = request.POST.get('curriculum', '')
            what_you_will_learn = request.POST.get('what_you_will_learn', '')
            category_id = request.POST.get('category')
            price = request.POST.get('price', '0.00')
            is_free = request.POST.get('is_free') == 'on'
            preview_video = request.POST.get('preview_video')
            is_published = request.POST.get('is_published') == 'on'
            allow_public_enrollment = request.POST.get('allow_public_enrollment') == 'on'
            
            # Validate required fields
            if not all([title, description, category_id]):
                messages.error(request, 'Please fill in all required fields.')
                return render(request, 'custom_admin/courses/form.html', {
                    'course': course,
                    'title': 'Edit Course',
                    'is_edit': True,
                    'categories': categories
                })
            
            # Get category
            category = get_object_or_404(Category, id=category_id)
            
            # Update course fields
            course.title = title
            course.description = description
            course.curriculum = curriculum
            course.what_you_will_learn = what_you_will_learn
            course.category = category
            course.price = float(price) if price else 0.00
            course.is_free = is_free
            course.preview_video = preview_video
            course.is_published = is_published
            course.allow_public_enrollment = allow_public_enrollment
            
            # Handle file upload
            thumbnail = request.FILES.get('thumbnail')
            if thumbnail:
                course.thumbnail = thumbnail
            
            course.save()
            
            messages.success(request, f'Course "{course.title}" updated successfully.')
            return redirect('custom_admin:course_detail', course_id=course.id)
            
        except Exception as e:
            messages.error(request, f'Error updating course: {str(e)}')
    
    return render(request, 'custom_admin/courses/form.html', {
        'course': course,
        'title': 'Edit Course',
        'is_edit': True,
        'categories': categories
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
    modules = Module.objects.select_related('course').order_by('title')
    
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
def module_detail_view(request, module_id):
    """View module details"""
    module = get_object_or_404(Module, id=module_id)
    
    # Get related content counts
    video_lessons = module.video_lessons.all()
    assignments = module.assignments.all()
    quizzes = module.quizzes.all()
    
    # Get module statistics
    enrollments_count = module.course.enrollments.count()
    progress_records = ModuleProgress.objects.filter(module=module)
    completions_count = progress_records.filter(is_completed=True).count()
    
    context = {
        'module': module,
        'video_lessons': video_lessons,
        'assignments': assignments,
        'quizzes': quizzes,
        'enrollments_count': enrollments_count,
        'completions_count': completions_count,
        'progress_records': progress_records,
    }
    
    return render(request, 'custom_admin/modules/detail.html', context)

@user_passes_test(is_staff_user)
def module_create_view(request):
    """Create a new module"""
    courses = Course.objects.prefetch_related('modules').all()
    
    if request.method == 'POST':
        try:
            # Get form data
            title = request.POST.get('title')
            description = request.POST.get('description')
            course_id = request.POST.get('course')
            order = request.POST.get('order')
            learning_objectives = request.POST.get('learning_objectives')
            duration_minutes = request.POST.get('duration_minutes')
            difficulty_level = request.POST.get('difficulty_level', 'beginner')
            is_active = request.POST.get('is_active') == 'on'
            prerequisites = request.POST.get('prerequisites')
            passing_score_percentage = request.POST.get('passing_score_percentage', 70)
            max_attempts = request.POST.get('max_attempts')
            requires_completion = request.POST.get('requires_completion') == 'on'
            resources = request.POST.get('resources')
            tags = request.POST.get('tags')
            
            # Validate required fields
            if not all([title, description, course_id, order]):
                messages.error(request, 'Please fill in all required fields.')
                return render(request, 'custom_admin/modules/form.html', {
                    'title': 'Add Module',
                    'is_edit': False,
                    'courses': courses
                })
            
            # Get course
            course = get_object_or_404(Course, id=course_id)
            
            # Create module
            module = Module.objects.create(
                title=title,
                description=description,
                course=course,
                order=int(order),
                learning_objectives=learning_objectives,
                duration_minutes=int(duration_minutes) if duration_minutes else None,
                difficulty_level=difficulty_level,
                is_active=is_active,
                prerequisites=prerequisites,
                passing_score_percentage=float(passing_score_percentage),
                max_attempts=int(max_attempts) if max_attempts else None,
                requires_completion=requires_completion,
                resources=resources,
                tags=tags
            )
            
            messages.success(request, f'Module "{module.title}" created successfully.')
            return redirect('custom_admin:module_detail', module_id=module.id)
            
        except Exception as e:
            messages.error(request, f'Error creating module: {str(e)}')
    
    return render(request, 'custom_admin/modules/form.html', {
        'title': 'Add Module',
        'is_edit': False,
        'courses': courses
    })

@user_passes_test(is_staff_user)
def module_edit_view(request, module_id):
    """Edit a module"""
    module = get_object_or_404(Module, id=module_id)
    courses = Course.objects.prefetch_related('modules').all()
    
    if request.method == 'POST':
        try:
            # Get form data
            title = request.POST.get('title')
            description = request.POST.get('description')
            course_id = request.POST.get('course')
            order = request.POST.get('order')
            learning_objectives = request.POST.get('learning_objectives')
            duration_minutes = request.POST.get('duration_minutes')
            difficulty_level = request.POST.get('difficulty_level', 'beginner')
            is_active = request.POST.get('is_active') == 'on'
            prerequisites = request.POST.get('prerequisites')
            passing_score_percentage = request.POST.get('passing_score_percentage', 70)
            max_attempts = request.POST.get('max_attempts')
            requires_completion = request.POST.get('requires_completion') == 'on'
            resources = request.POST.get('resources')
            tags = request.POST.get('tags')
            
            # Validate required fields
            if not all([title, description, course_id, order]):
                messages.error(request, 'Please fill in all required fields.')
                return render(request, 'custom_admin/modules/form.html', {
                    'module': module,
                    'title': 'Edit Module',
                    'is_edit': True,
                    'courses': courses
                })
            
            # Get course
            course = get_object_or_404(Course, id=course_id)
            
            # Update module
            module.title = title
            module.description = description
            module.course = course
            module.order = int(order)
            module.learning_objectives = learning_objectives
            module.duration_minutes = int(duration_minutes) if duration_minutes else None
            module.difficulty_level = difficulty_level
            module.is_active = is_active
            module.prerequisites = prerequisites
            module.passing_score_percentage = float(passing_score_percentage)
            module.max_attempts = int(max_attempts) if max_attempts else None
            module.requires_completion = requires_completion
            module.resources = resources
            module.tags = tags
            module.save()
            
            messages.success(request, f'Module "{module.title}" updated successfully.')
            return redirect('custom_admin:module_detail', module_id=module.id)
            
        except Exception as e:
            messages.error(request, f'Error updating module: {str(e)}')
    
    return render(request, 'custom_admin/modules/form.html', {
        'module': module,
        'title': 'Edit Module',
        'is_edit': True,
        'courses': courses
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
    lessons = VideoLesson.objects.select_related('module', 'module__course').order_by('title')
    
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
    if request.method == 'POST':
        form = CustomVideoLessonForm(request.POST, request.FILES)
        if form.is_valid():
            video_lesson = form.save()
            messages.success(request, f'Video lesson "{video_lesson.title}" created successfully.')
            return redirect('custom_admin:video_lessons_list')
    else:
        form = CustomVideoLessonForm()
    
    courses = Course.objects.prefetch_related('modules').all()
    return render(request, 'custom_admin/video_lessons/form.html', {
        'form': form,
        'title': 'Add Video Lesson',
        'is_edit': False,
        'courses': courses
    })

@user_passes_test(is_staff_user)
def video_lesson_edit_view(request, lesson_id):
    """Edit a video lesson"""
    lesson = get_object_or_404(VideoLesson, id=lesson_id)
    
    if request.method == 'POST':
        form = CustomVideoLessonForm(request.POST, request.FILES, instance=lesson)
        if form.is_valid():
            video_lesson = form.save()
            messages.success(request, f'Video lesson "{video_lesson.title}" updated successfully.')
            return redirect('custom_admin:video_lessons_list')
    else:
        form = CustomVideoLessonForm(instance=lesson)
    
    courses = Course.objects.prefetch_related('modules').all()
    return render(request, 'custom_admin/video_lessons/form.html', {
        'form': form,
        'lesson': lesson,
        'title': 'Edit Video Lesson',
        'is_edit': True,
        'courses': courses
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
    notifications = Notification.objects.select_related('user').order_by('-created_at')
    
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
    from .forms import CustomEnrollmentForm
    
    if request.method == 'POST':
        form = CustomEnrollmentForm(request.POST)
        if form.is_valid():
            enrollment = form.save()
            
            # Check if user wants to create installment plan
            if form.cleaned_data.get('has_installment_plan'):
                messages.success(request, f'Enrollment for "{enrollment.user.name}" created successfully. Now create the installment plan.')
                # Pass enrollment ID to pre-select it in the installment plan form
                return redirect(f'{reverse("custom_admin:installment_plan_create")}?enrollment={enrollment.id}')
            else:
                messages.success(request, f'Enrollment for "{enrollment.user.name}" in "{enrollment.course.title}" created successfully.')
                return redirect('custom_admin:enrollments_list')
    else:
        form = CustomEnrollmentForm()
    
    context = {
        'form': form,
        'title': 'Add New Enrollment',
        'is_edit': False,
        'enrollment': None
    }
    return render(request, 'custom_admin/enrollments/form.html', context)

@user_passes_test(is_staff_user)
def enrollment_edit_view(request, enrollment_id):
    """Edit enrollment"""
    from .forms import CustomEnrollmentForm
    
    enrollment = get_object_or_404(Enrollment, id=enrollment_id)
    
    if request.method == 'POST':
        form = CustomEnrollmentForm(request.POST, instance=enrollment)
        if form.is_valid():
            enrollment = form.save()
            messages.success(request, f'Enrollment for "{enrollment.user.name}" in "{enrollment.course.title}" updated successfully.')
            return redirect('custom_admin:enrollments_list')
    else:
        form = CustomEnrollmentForm(instance=enrollment)
    
    context = {
        'form': form,
        'title': f'Edit Enrollment: {enrollment.user.name} - {enrollment.course.title}',
        'is_edit': True,
        'enrollment': enrollment
    }
    return render(request, 'custom_admin/enrollments/form.html', context)

@user_passes_test(is_staff_user)
def enrollment_delete_view(request, enrollment_id):
    """Delete enrollment"""
    enrollment = get_object_or_404(Enrollment, id=enrollment_id)
    if request.method == 'POST':
        user_name = enrollment.user.name
        course_title = enrollment.course.title
        enrollment.delete()
        messages.success(request, f'Enrollment for "{user_name}" in "{course_title}" deleted successfully.')
        return redirect('custom_admin:enrollments_list')
    return render(request, 'custom_admin/enrollments/delete.html', {'enrollment': enrollment})

@user_passes_test(is_staff_user)
def installment_plans_list_view(request):
    """List installment plans"""
    search_query = request.GET.get('search', '')
    plans = InstallmentPlan.objects.select_related('enrollment', 'enrollment__user', 'enrollment__course').prefetch_related('enrollment__payments').order_by('-created_at')
    
    if search_query:
        plans = plans.filter(
            Q(enrollment__user__name__icontains=search_query) |
            Q(enrollment__course__title__icontains=search_query)
        )
    
    # Add completed payments count to each plan
    for plan in plans:
        if plan.enrollment:
            plan.completed_payments_count = plan.enrollment.payments.filter(status='completed').count()
        else:
            plan.completed_payments_count = 0
    
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
    from .forms import CustomInstallmentPlanForm
    
    if request.method == 'POST':
        form = CustomInstallmentPlanForm(request.POST)
        if form.is_valid():
            plan = form.save()
            messages.success(request, f'Installment plan for "{plan.enrollment.user.name}" created successfully.')
            return redirect('custom_admin:installment_plans_list')
    else:
        # Check if enrollment ID is passed from enrollment creation
        enrollment_id = request.GET.get('enrollment')
        initial_data = {}
        
        if enrollment_id:
            try:
                enrollment = Enrollment.objects.get(id=enrollment_id)
                initial_data['enrollment'] = enrollment
                # Set suggested values based on enrollment
                if enrollment.total_amount:
                    # Suggest 3 installments by default
                    suggested_installments = 3
                    suggested_amount = enrollment.total_amount / suggested_installments
                    initial_data['total_installments'] = suggested_installments
                    initial_data['installment_amount'] = suggested_amount
            except Enrollment.DoesNotExist:
                pass
        
        form = CustomInstallmentPlanForm(initial=initial_data)
    
    context = {
        'form': form,
        'title': 'Add Installment Plan',
        'is_edit': False,
        'plan': None
    }
    return render(request, 'custom_admin/installment_plans/form.html', context)

@user_passes_test(is_staff_user)
def installment_plan_edit_view(request, plan_id):
    """Edit installment plan"""
    from .forms import CustomInstallmentPlanForm
    
    plan = get_object_or_404(InstallmentPlan, id=plan_id)
    # Add completed payments count
    plan.completed_payments_count = plan.enrollment.payments.filter(status='completed').count()
    
    if request.method == 'POST':
        form = CustomInstallmentPlanForm(request.POST, instance=plan)
        if form.is_valid():
            plan = form.save()
            messages.success(request, f'Installment plan for "{plan.enrollment.user.name}" updated successfully.')
            return redirect('custom_admin:installment_plans_list')
    else:
        form = CustomInstallmentPlanForm(instance=plan)
    
    context = {
        'form': form,
        'title': f'Edit Plan: {plan.enrollment.user.name}',
        'is_edit': True,
        'plan': plan
    }
    return render(request, 'custom_admin/installment_plans/form.html', context)

@user_passes_test(is_staff_user)
def installment_plan_delete_view(request, plan_id):
    """Delete installment plan"""
    plan = get_object_or_404(InstallmentPlan, id=plan_id)
    # Add completed payments count
    plan.completed_payments_count = plan.enrollment.payments.filter(status='completed').count()
    
    if request.method == 'POST':
        user_name = plan.enrollment.user.name
        # Update enrollment to indicate it no longer has installment plan
        plan.enrollment.has_installment_plan = False
        plan.enrollment.save()
        plan.delete()
        messages.success(request, f'Installment plan for "{user_name}" deleted successfully.')
        return redirect('custom_admin:installment_plans_list')
    return render(request, 'custom_admin/installment_plans/delete.html', {'plan': plan})

@user_passes_test(is_staff_user)
def payment_create_view(request):
    """Create payment"""
    
    if request.method == 'POST':
        try:
            # Get form data
            enrollment_id = request.POST.get('enrollment')
            installment_number = request.POST.get('installment_number')
            amount = request.POST.get('amount')
            tax_amount = request.POST.get('tax_amount')
            payment_method = request.POST.get('payment_method')
            status = request.POST.get('status')
            transaction_id = request.POST.get('transaction_id')
            invoice_number = request.POST.get('invoice_number')
            payment_date = request.POST.get('payment_date')
            due_date = request.POST.get('due_date')
            notes = request.POST.get('notes')
            
            # Validate required fields
            if not all([enrollment_id, installment_number, amount, tax_amount, payment_method, status, due_date]):
                messages.error(request, 'Please fill in all required fields.')
                return redirect('custom_admin:payment_create')
            
            # Get enrollment
            enrollment = get_object_or_404(Enrollment, id=enrollment_id)
            
            # Check if payment with this installment number already exists
            if Payment.objects.filter(enrollment=enrollment, installment_number=installment_number).exists():
                messages.error(request, f'Payment with installment number {installment_number} already exists for this enrollment.')
                return redirect('custom_admin:payment_create')
            
            # Create payment
            payment = Payment.objects.create(
                enrollment=enrollment,
                installment_number=int(installment_number),
                amount=float(amount),
                tax_amount=float(tax_amount),
                payment_method=payment_method,
                status=status,
                transaction_id=transaction_id if transaction_id else None,
                invoice_number=invoice_number if invoice_number else None,
                payment_date=payment_date if payment_date else None,
                due_date=due_date,
                notes=notes if notes else None
            )
            
            # Auto-generate tax invoice if requested and payment is completed
            generate_tax_invoice = request.POST.get('generate_tax_invoice') == 'on'
            if generate_tax_invoice and status == 'completed':
                from datetime import datetime
                auto_invoice_number = f"INV-{enrollment.id}-{payment.id}-{datetime.now().strftime('%Y%m%d%H%M%S')}"
                
                TaxInvoice.objects.create(
                    enrollment=enrollment,
                    payment=payment,
                    invoice_number=auto_invoice_number,
                    subtotal=float(amount),
                    tax_rate=18.0,  # 18% GST
                    tax_amount=float(tax_amount),
                    total_amount=float(amount) + float(tax_amount)
                )
            
            # Update enrollment payment status
            enrollment.payment_status = 'partial' if enrollment.outstanding_amount > 0 else 'completed'
            enrollment.save()
            
            success_message = f'Payment created successfully for {enrollment.user.name}.'
            if generate_tax_invoice and status == 'completed' and float(tax_amount) > 0:
                success_message += ' Tax invoice generated automatically.'
            messages.success(request, success_message)
            return redirect('custom_admin:payments_list')
            
        except Exception as e:
            messages.error(request, f'Error creating payment: {str(e)}')
    
    # Get all enrollments with outstanding amounts for dropdown
    enrollments = Enrollment.objects.select_related('user', 'course').filter(
        payment_status__in=['pending', 'partial']
    ).order_by('user__name')
    
    context = {
        'title': 'Add Payment',
        'is_edit': False,
        'enrollments': enrollments,
    }
    return render(request, 'custom_admin/payments/form.html', context)

@user_passes_test(is_staff_user)
def payment_edit_view(request, payment_id):
    """Edit payment"""
    payment = get_object_or_404(Payment, id=payment_id)
    
    if request.method == 'POST':
        try:
            # Get form data (enrollment cannot be changed when editing)
            installment_number = request.POST.get('installment_number')
            amount = request.POST.get('amount')
            tax_amount = request.POST.get('tax_amount')
            payment_method = request.POST.get('payment_method')
            status = request.POST.get('status')
            transaction_id = request.POST.get('transaction_id')
            invoice_number = request.POST.get('invoice_number')
            payment_date = request.POST.get('payment_date')
            due_date = request.POST.get('due_date')
            notes = request.POST.get('notes')
            
            # Validate required fields
            if not all([installment_number, amount, tax_amount, payment_method, status, due_date]):
                messages.error(request, 'Please fill in all required fields.')
                return redirect('custom_admin:payment_edit', payment_id=payment_id)
            
            # Check if installment number conflict (exclude current payment)
            existing_payment = Payment.objects.filter(
                enrollment=payment.enrollment, 
                installment_number=installment_number
            ).exclude(id=payment_id).first()
            
            if existing_payment:
                messages.error(request, f'Payment with installment number {installment_number} already exists for this enrollment.')
                return redirect('custom_admin:payment_edit', payment_id=payment_id)
            
            # Store old status to check if it changed
            old_status = payment.status
            
            # Update payment
            payment.installment_number = int(installment_number)
            payment.amount = float(amount)
            payment.tax_amount = float(tax_amount)
            payment.payment_method = payment_method
            payment.status = status
            payment.transaction_id = transaction_id if transaction_id else None
            payment.invoice_number = invoice_number if invoice_number else None
            payment.payment_date = payment_date if payment_date else None
            payment.due_date = due_date
            payment.notes = notes if notes else None
            payment.save()
            
            # Auto-generate tax invoice if requested and status changed to completed
            generate_tax_invoice = request.POST.get('generate_tax_invoice') == 'on'
            should_generate_invoice = (
                generate_tax_invoice and 
                old_status != 'completed' and 
                status == 'completed'
            )
            
            if should_generate_invoice:
                # Check if tax invoice already exists for this payment
                if not TaxInvoice.objects.filter(payment=payment).exists():
                    from datetime import datetime
                    auto_invoice_number = f"INV-{payment.enrollment.id}-{payment.id}-{datetime.now().strftime('%Y%m%d%H%M%S')}"
                    
                    TaxInvoice.objects.create(
                        enrollment=payment.enrollment,
                        payment=payment,
                        invoice_number=auto_invoice_number,
                        subtotal=float(amount),
                        tax_rate=18.0,  # 18% GST
                        tax_amount=float(tax_amount),
                        total_amount=float(amount) + float(tax_amount)
                    )
            
            # Update enrollment payment status
            enrollment = payment.enrollment
            enrollment.payment_status = 'partial' if enrollment.outstanding_amount > 0 else 'completed'
            enrollment.save()
            
            success_message = f'Payment updated successfully for {payment.enrollment.user.name}.'
            if should_generate_invoice:
                success_message += ' Tax invoice generated automatically.'
            messages.success(request, success_message)
            return redirect('custom_admin:payments_list')
            
        except Exception as e:
            messages.error(request, f'Error updating payment: {str(e)}')
    
    # Get all enrollments for context (though enrollment cannot be changed)
    enrollments = Enrollment.objects.select_related('user', 'course').order_by('user__name')
    
    context = {
        'payment': payment,
        'title': 'Edit Payment',
        'is_edit': True,
        'enrollments': enrollments,
    }
    return render(request, 'custom_admin/payments/form.html', context)

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
    invoices = TaxInvoice.objects.select_related('enrollment', 'enrollment__user', 'payment').order_by('-created_at')
    
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
    from datetime import date
    
    if request.method == 'POST':
        try:
            enrollment_id = request.POST.get('enrollment')
            payment_id = request.POST.get('payment')
            invoice_number = request.POST.get('invoice_number')
            invoice_date = request.POST.get('invoice_date')
            subtotal = request.POST.get('subtotal')
            tax_rate = request.POST.get('tax_rate')
            tax_amount = request.POST.get('tax_amount')
            total_amount = request.POST.get('total_amount')
            
            # Validate required fields
            if not all([enrollment_id, invoice_number, invoice_date, subtotal, tax_rate, tax_amount, total_amount]):
                messages.error(request, 'Please fill in all required fields.')
                return redirect('custom_admin:tax_invoice_create')
            
            enrollment = get_object_or_404(Enrollment, id=enrollment_id)
            payment = get_object_or_404(Payment, id=payment_id) if payment_id else None
            
            # Check if invoice number already exists
            if TaxInvoice.objects.filter(invoice_number=invoice_number).exists():
                messages.error(request, f'Invoice number {invoice_number} already exists.')
                return redirect('custom_admin:tax_invoice_create')
            
            # Create tax invoice
            TaxInvoice.objects.create(
                enrollment=enrollment,
                payment=payment,
                invoice_number=invoice_number,
                invoice_date=invoice_date,
                subtotal=float(subtotal),
                tax_rate=float(tax_rate),
                tax_amount=float(tax_amount),
                total_amount=float(total_amount)
            )
            
            messages.success(request, f'Tax invoice {invoice_number} created successfully.')
            return redirect('custom_admin:tax_invoices_list')
            
        except Exception as e:
            messages.error(request, f'Error creating tax invoice: {str(e)}')
    
    # Get context data
    enrollments = Enrollment.objects.select_related('user', 'course').order_by('user__name')
    payments = Payment.objects.select_related('enrollment__user').filter(status='completed').order_by('-payment_date')
    
    # Generate suggested invoice number
    from datetime import datetime
    suggested_number = f"{datetime.now().strftime('%Y%m%d%H%M%S')}"
    
    context = {
        'title': 'Generate Tax Invoice',
        'is_edit': False,
        'enrollments': enrollments,
        'payments': payments,
        'suggested_invoice_number': suggested_number,
        'today': date.today().strftime('%Y-%m-%d')
    }
    
    return render(request, 'custom_admin/tax_invoices/form.html', context)

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
    search_query = request.GET.get('search', '')
    memberships = TeamMembership.objects.select_related('team', 'user').all().order_by('team__name', 'user__name')
    
    if search_query:
        memberships = memberships.filter(
            Q(user__name__icontains=search_query) |
            Q(user__email__icontains=search_query) |
            Q(team__name__icontains=search_query)
        )
    
    paginator = Paginator(memberships, 25)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'page_obj': page_obj,
        'search_query': search_query,
    }
    
    return render(request, 'custom_admin/team_memberships/list.html', context)

@user_passes_test(is_staff_user)
def team_membership_create_view(request):
    """Create team membership"""
    from .forms import CustomTeamMembershipForm
    
    if request.method == 'POST':
        form = CustomTeamMembershipForm(request.POST)
        if form.is_valid():
            membership = form.save()
            messages.success(request, f'Added "{membership.user.name}" to team "{membership.team.name}" successfully.')
            return redirect('custom_admin:team_memberships_list')
    else:
        form = CustomTeamMembershipForm()
    
    context = {
        'form': form,
        'title': 'Add Team Membership',
        'is_edit': False,
        'membership': None
    }
    return render(request, 'custom_admin/team_memberships/form.html', context)

@user_passes_test(is_staff_user)
def team_membership_edit_view(request, membership_id):
    """Edit team membership"""
    from .forms import CustomTeamMembershipForm
    
    membership = get_object_or_404(TeamMembership, id=membership_id)
    
    if request.method == 'POST':
        form = CustomTeamMembershipForm(request.POST, instance=membership)
        if form.is_valid():
            membership = form.save()
            messages.success(request, f'Updated membership for "{membership.user.name}" in team "{membership.team.name}".')
            return redirect('custom_admin:team_memberships_list')
    else:
        form = CustomTeamMembershipForm(instance=membership)
    
    context = {
        'form': form,
        'title': f'Edit Membership: {membership.user.name} - {membership.team.name}',
        'is_edit': True,
        'membership': membership
    }
    return render(request, 'custom_admin/team_memberships/form.html', context)

@user_passes_test(is_staff_user)
def team_membership_delete_view(request, membership_id):
    """Delete team membership"""
    membership = get_object_or_404(TeamMembership, id=membership_id)
    if request.method == 'POST':
        user_name = membership.user.name
        team_name = membership.team.name
        membership.delete()
        messages.success(request, f'Removed "{user_name}" from team "{team_name}" successfully.')
        return redirect('custom_admin:team_memberships_list')
    return render(request, 'custom_admin/team_memberships/delete.html', {'membership': membership})

@user_passes_test(is_staff_user)
def team_create_view(request):
    """Create team"""
    from .forms import CustomTeamForm
    
    if request.method == 'POST':
        form = CustomTeamForm(request.POST)
        if form.is_valid():
            team = form.save()
            messages.success(request, f'Team "{team.name}" created successfully.')
            return redirect('custom_admin:teams_list')
    else:
        form = CustomTeamForm(initial={'created_by': request.user})
    
    context = {
        'form': form,
        'title': 'Add New Team',
        'is_edit': False,
        'team': None
    }
    return render(request, 'custom_admin/teams/form.html', context)

@user_passes_test(is_staff_user)
def team_edit_view(request, team_id):
    """Edit team"""
    from .forms import CustomTeamForm
    
    team = get_object_or_404(Team, id=team_id)
    
    if request.method == 'POST':
        form = CustomTeamForm(request.POST, instance=team)
        if form.is_valid():
            team = form.save()
            messages.success(request, f'Team "{team.name}" updated successfully.')
            return redirect('custom_admin:teams_list')
    else:
        form = CustomTeamForm(instance=team)
    
    context = {
        'form': form,
        'title': f'Edit Team: {team.name}',
        'is_edit': True,
        'team': team
    }
    return render(request, 'custom_admin/teams/form.html', context)

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
    from .forms import CustomUserCreationForm
    
    if request.method == 'POST':
        form = CustomUserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            messages.success(request, f'User "{user.name}" created successfully.')
            return redirect('custom_admin:users_list')
    else:
        form = CustomUserCreationForm()
    
    context = {
        'form': form,
        'title': 'Add New User',
        'is_edit': False,
        'user': None
    }
    return render(request, 'custom_admin/users/form.html', context)

@user_passes_test(is_staff_user)
def user_edit_view(request, user_id):
    """Edit user"""
    from .forms import CustomUserChangeForm
    
    user = get_object_or_404(User, id=user_id)
    
    if request.method == 'POST':
        form = CustomUserChangeForm(request.POST, instance=user)
        if form.is_valid():
            user = form.save()
            messages.success(request, f'User "{user.name}" updated successfully.')
            return redirect('custom_admin:user_detail', user_id=user.id)
    else:
        form = CustomUserChangeForm(instance=user)
    
    context = {
        'form': form,
        'title': f'Edit User: {user.name}',
        'is_edit': True,
        'user': user
    }
    return render(request, 'custom_admin/users/form.html', context)

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
    search_query = request.GET.get('search', '')
    configs = YouTubeChannelConfig.objects.select_related('admin_user').all().order_by('channel_name')
    
    if search_query:
        configs = configs.filter(
            Q(channel_name__icontains=search_query) |
            Q(channel_id__icontains=search_query) |
            Q(admin_user__name__icontains=search_query)
        )
    
    paginator = Paginator(configs, 25)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'page_obj': page_obj,
        'search_query': search_query,
    }
    
    return render(request, 'custom_admin/youtube_channel_configs/list.html', context)

@user_passes_test(is_staff_user)
def youtube_channel_config_create_view(request):
    """Create YouTube channel config"""
    from .forms import CustomYouTubeChannelConfigForm
    
    if request.method == 'POST':
        form = CustomYouTubeChannelConfigForm(request.POST)
        if form.is_valid():
            config = form.save()
            messages.success(request, f'YouTube channel config "{config.channel_name}" created successfully.')
            return redirect('custom_admin:youtube_channel_configs_list')
    else:
        form = CustomYouTubeChannelConfigForm(initial={'admin_user': request.user})
    
    context = {
        'form': form,
        'title': 'Add YouTube Channel Config',
        'is_edit': False,
        'config': None
    }
    return render(request, 'custom_admin/youtube_channel_configs/form.html', context)

@user_passes_test(is_staff_user)
def youtube_channel_config_edit_view(request, config_id):
    """Edit YouTube channel config"""
    from .forms import CustomYouTubeChannelConfigForm
    
    config = get_object_or_404(YouTubeChannelConfig, id=config_id)
    
    if request.method == 'POST':
        form = CustomYouTubeChannelConfigForm(request.POST, instance=config)
        if form.is_valid():
            config = form.save()
            messages.success(request, f'YouTube channel config "{config.channel_name}" updated successfully.')
            return redirect('custom_admin:youtube_channel_configs_list')
    else:
        form = CustomYouTubeChannelConfigForm(instance=config)
    
    context = {
        'form': form,
        'title': f'Edit Channel: {config.channel_name}',
        'is_edit': True,
        'config': config
    }
    return render(request, 'custom_admin/youtube_channel_configs/form.html', context)

@user_passes_test(is_staff_user)
def youtube_channel_config_delete_view(request, config_id):
    """Delete YouTube channel config"""
    config = get_object_or_404(YouTubeChannelConfig, id=config_id)
    if request.method == 'POST':
        channel_name = config.channel_name
        config.delete()
        messages.success(request, f'YouTube channel config "{channel_name}" deleted successfully.')
        return redirect('custom_admin:youtube_channel_configs_list')
    return render(request, 'custom_admin/youtube_channel_configs/delete.html', {'config': config})

@user_passes_test(is_staff_user)
def youtube_videos_list_view(request):
    """List YouTube videos"""
    search_query = request.GET.get('search', '')
    videos = YouTubeVideo.objects.select_related('channel_config').all().order_by('title')
    
    if search_query:
        videos = videos.filter(
            Q(title__icontains=search_query) |
            Q(channel_config__channel_name__icontains=search_query) |
            Q(video_id__icontains=search_query)
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
    from .forms import CustomYouTubeVideoForm
    
    if request.method == 'POST':
        form = CustomYouTubeVideoForm(request.POST)
        if form.is_valid():
            video = form.save()
            messages.success(request, f'YouTube video "{video.title}" created successfully.')
            return redirect('custom_admin:youtube_videos_list')
    else:
        form = CustomYouTubeVideoForm()
    
    context = {
        'form': form,
        'title': 'Add YouTube Video',
        'is_edit': False,
        'video': None
    }
    return render(request, 'custom_admin/youtube_videos/form.html', context)

@user_passes_test(is_staff_user)
def youtube_video_edit_view(request, video_id):
    """Edit YouTube video"""
    from .forms import CustomYouTubeVideoForm
    
    video = get_object_or_404(YouTubeVideo, id=video_id)
    
    if request.method == 'POST':
        form = CustomYouTubeVideoForm(request.POST, instance=video)
        if form.is_valid():
            video = form.save()
            messages.success(request, f'YouTube video "{video.title}" updated successfully.')
            return redirect('custom_admin:youtube_videos_list')
    else:
        form = CustomYouTubeVideoForm(instance=video)
    
    context = {
        'form': form,
        'title': f'Edit Video: {video.title}',
        'is_edit': True,
        'video': video
    }
    return render(request, 'custom_admin/youtube_videos/form.html', context)

@user_passes_test(is_staff_user)
def youtube_video_delete_view(request, video_id):
    """Delete YouTube video"""
    video = get_object_or_404(YouTubeVideo, id=video_id)
    if request.method == 'POST':
        video.delete()
        messages.success(request, f'YouTube video "{video.title}" deleted successfully.')
        return redirect('custom_admin:youtube_videos_list')
    return render(request, 'custom_admin/youtube_videos/delete.html', {'video': video})


# ==============================================================================
# ASSIGNMENTS MANAGEMENT VIEWS
# ==============================================================================

@user_passes_test(is_staff_user)
def assignments_list_view(request):
    """List all assignments"""
    search_query = request.GET.get('search', '')
    assignments = Assignment.objects.select_related('module', 'module__course').order_by('title')
    
    if search_query:
        assignments = assignments.filter(
            Q(title__icontains=search_query) |
            Q(module__title__icontains=search_query) |
            Q(module__course__title__icontains=search_query)
        )
    
    paginator = Paginator(assignments, 25)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'page_obj': page_obj,
        'search_query': search_query,
    }
    
    return render(request, 'custom_admin/assignments/list.html', context)

@user_passes_test(is_staff_user)
def assignment_detail_view(request, assignment_id):
    """View assignment details"""
    assignment = get_object_or_404(Assignment, id=assignment_id)
    submissions = AssignmentSubmission.objects.filter(assignment=assignment).select_related('student')
    
    context = {
        'assignment': assignment,
        'submissions': submissions,
    }
    
    return render(request, 'custom_admin/assignments/detail.html', context)

@user_passes_test(is_staff_user)
def assignment_create_view(request):
    """Create assignment"""
    if request.method == 'POST':
        form = CustomAssignmentForm(request.POST)
        if form.is_valid():
            assignment = form.save()
            messages.success(request, f'Assignment "{assignment.title}" created successfully.')
            return redirect('custom_admin:assignments_list')
    else:
        form = CustomAssignmentForm()
    
    courses = Course.objects.prefetch_related('modules').all()
    return render(request, 'custom_admin/assignments/form.html', {
        'form': form,
        'title': 'Add Assignment',
        'is_edit': False,
        'courses': courses
    })

@user_passes_test(is_staff_user)
def assignment_edit_view(request, assignment_id):
    """Edit assignment"""
    assignment = get_object_or_404(Assignment, id=assignment_id)
    
    if request.method == 'POST':
        form = CustomAssignmentForm(request.POST, instance=assignment)
        if form.is_valid():
            assignment = form.save()
            messages.success(request, f'Assignment "{assignment.title}" updated successfully.')
            return redirect('custom_admin:assignments_list')
    else:
        form = CustomAssignmentForm(instance=assignment)
    
    courses = Course.objects.prefetch_related('modules').all()
    return render(request, 'custom_admin/assignments/form.html', {
        'form': form,
        'assignment': assignment,
        'title': 'Edit Assignment',
        'is_edit': True,
        'courses': courses
    })

@user_passes_test(is_staff_user)
def assignment_delete_view(request, assignment_id):
    """Delete assignment"""
    assignment = get_object_or_404(Assignment, id=assignment_id)
    if request.method == 'POST':
        assignment.delete()
        messages.success(request, f'Assignment "{assignment.title}" deleted successfully.')
        return redirect('custom_admin:assignments_list')
    return render(request, 'custom_admin/assignments/delete.html', {'assignment': assignment})


# ==============================================================================
# ASSIGNMENT SUBMISSIONS MANAGEMENT VIEWS
# ==============================================================================

@user_passes_test(is_staff_user)
def assignment_submissions_list_view(request):
    """List all assignment submissions"""
    search_query = request.GET.get('search', '')
    status_filter = request.GET.get('status', '')
    
    submissions = AssignmentSubmission.objects.select_related(
        'assignment', 'student', 'assignment__module', 'assignment__module__course'
    ).order_by('-submitted_at')
    
    if search_query:
        submissions = submissions.filter(
            Q(student__name__icontains=search_query) |
            Q(assignment__title__icontains=search_query) |
            Q(assignment__module__course__title__icontains=search_query)
        )
    
    if status_filter:
        submissions = submissions.filter(status=status_filter)
    
    # Calculate statistics
    all_submissions = AssignmentSubmission.objects.all()
    stats = {
        'total': all_submissions.count(),
        'pending': all_submissions.filter(status__in=['submitted', 'under_review']).count(),
        'graded': all_submissions.filter(status='graded').count(),
        'returned': all_submissions.filter(status='returned').count(),
    }
    
    paginator = Paginator(submissions, 25)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'page_obj': page_obj,
        'search_query': search_query,
        'status_filter': status_filter,
        'stats': stats,
    }
    
    return render(request, 'custom_admin/assignment_submissions/list.html', context)

@user_passes_test(is_staff_user)
def assignment_submission_detail_view(request, submission_id):
    """View and grade assignment submission"""
    submission = get_object_or_404(AssignmentSubmission, id=submission_id)
    
    if request.method == 'POST':
        score = request.POST.get('score')
        comments = request.POST.get('grade_comments', '')
        
        if score:
            try:
                score = int(score)
                if 0 <= score <= submission.assignment.max_points:
                    submission.grade(score, comments, request.user)
                    messages.success(request, f'Assignment graded successfully. Score: {score}/{submission.assignment.max_points}')
                    return redirect('custom_admin:assignment_submission_detail', submission_id=submission.id)
                else:
                    messages.error(request, f'Score must be between 0 and {submission.assignment.max_points}')
            except ValueError:
                messages.error(request, 'Please enter a valid score.')
        else:
            messages.error(request, 'Score is required.')
    
    context = {
        'submission': submission,
    }
    
    return render(request, 'custom_admin/assignment_submissions/detail.html', context)


# ==============================================================================
# QUIZZES MANAGEMENT VIEWS
# ==============================================================================

@user_passes_test(is_staff_user)
def quizzes_list_view(request):
    """List all quizzes"""
    search_query = request.GET.get('search', '')
    quizzes = Quiz.objects.select_related('module', 'module__course').annotate(
        questions_count=Count('questions'),
        attempts_count=Count('attempts')
    ).order_by('title')
    
    if search_query:
        quizzes = quizzes.filter(
            Q(title__icontains=search_query) |
            Q(module__title__icontains=search_query) |
            Q(module__course__title__icontains=search_query)
        )
    
    paginator = Paginator(quizzes, 25)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'page_obj': page_obj,
        'search_query': search_query,
    }
    
    return render(request, 'custom_admin/quizzes/list.html', context)

@user_passes_test(is_staff_user)
def quiz_detail_view(request, quiz_id):
    """View quiz details"""
    quiz = get_object_or_404(Quiz, id=quiz_id)
    questions = QuizQuestion.objects.filter(quiz=quiz).prefetch_related('choices').order_by('order')
    attempts = QuizAttempt.objects.filter(quiz=quiz).select_related('student').order_by('-started_at')[:10]
    
    context = {
        'quiz': quiz,
        'questions': questions,
        'recent_attempts': attempts,
    }
    
    return render(request, 'custom_admin/quizzes/detail.html', context)

@user_passes_test(is_staff_user)
def quiz_create_view(request):
    """Create quiz"""
    courses = Course.objects.prefetch_related('modules').all()
    
    if request.method == 'POST':
        try:
            # Get form data
            title = request.POST.get('title')
            description = request.POST.get('description')
            module_id = request.POST.get('module')
            time_limit = request.POST.get('time_limit')
            max_attempts = request.POST.get('max_attempts')
            passing_score = request.POST.get('passing_score', 70)
            is_required = request.POST.get('is_required') == 'on'
            show_results_immediately = request.POST.get('show_results_immediately') == 'on'
            randomize_questions = request.POST.get('randomize_questions') == 'on'
            order = request.POST.get('order', 1)
            
            # Validate required fields
            if not all([title, description, module_id]):
                messages.error(request, 'Please fill in all required fields.')
                return render(request, 'custom_admin/quizzes/form.html', {
                    'title': 'Add Quiz',
                    'is_edit': False,
                    'courses': courses
                })
            
            # Get module
            module = get_object_or_404(Module, id=module_id)
            
            # Create quiz
            quiz = Quiz.objects.create(
                title=title,
                description=description,
                module=module,
                time_limit=int(time_limit) if time_limit else 30,
                max_attempts=int(max_attempts) if max_attempts else 3,
                passing_score=int(passing_score),
                is_required=is_required,
                show_results_immediately=show_results_immediately,
                randomize_questions=randomize_questions,
                order=int(order)
            )
            
            messages.success(request, f'Quiz "{quiz.title}" created successfully.')
            return redirect('custom_admin:quiz_detail', quiz_id=quiz.id)
            
        except Exception as e:
            messages.error(request, f'Error creating quiz: {str(e)}')
    
    return render(request, 'custom_admin/quizzes/form.html', {
        'title': 'Add Quiz',
        'is_edit': False,
        'courses': courses
    })

@user_passes_test(is_staff_user)
def quiz_edit_view(request, quiz_id):
    """Edit quiz"""
    quiz = get_object_or_404(Quiz, id=quiz_id)
    courses = Course.objects.prefetch_related('modules').all()
    
    if request.method == 'POST':
        try:
            # Get form data
            title = request.POST.get('title')
            description = request.POST.get('description')
            module_id = request.POST.get('module')
            time_limit = request.POST.get('time_limit')
            max_attempts = request.POST.get('max_attempts')
            passing_score = request.POST.get('passing_score', 70)
            is_required = request.POST.get('is_required') == 'on'
            show_results_immediately = request.POST.get('show_results_immediately') == 'on'
            randomize_questions = request.POST.get('randomize_questions') == 'on'
            order = request.POST.get('order', 1)
            
            # Validate required fields
            if not all([title, description, module_id]):
                messages.error(request, 'Please fill in all required fields.')
                return render(request, 'custom_admin/quizzes/form.html', {
                    'quiz': quiz,
                    'title': 'Edit Quiz',
                    'is_edit': True,
                    'courses': courses
                })
            
            # Get module
            module = get_object_or_404(Module, id=module_id)
            
            # Update quiz fields
            quiz.title = title
            quiz.description = description
            quiz.module = module
            quiz.time_limit = int(time_limit) if time_limit else 30
            quiz.max_attempts = int(max_attempts) if max_attempts else 3
            quiz.passing_score = int(passing_score)
            quiz.is_required = is_required
            quiz.show_results_immediately = show_results_immediately
            quiz.randomize_questions = randomize_questions
            quiz.order = int(order)
            quiz.save()
            
            messages.success(request, f'Quiz "{quiz.title}" updated successfully.')
            return redirect('custom_admin:quiz_detail', quiz_id=quiz.id)
            
        except Exception as e:
            messages.error(request, f'Error updating quiz: {str(e)}')
    
    return render(request, 'custom_admin/quizzes/form.html', {
        'quiz': quiz,
        'title': 'Edit Quiz',
        'is_edit': True,
        'courses': courses
    })

@user_passes_test(is_staff_user)
def quiz_delete_view(request, quiz_id):
    """Delete quiz"""
    quiz = get_object_or_404(Quiz, id=quiz_id)
    if request.method == 'POST':
        quiz.delete()
        messages.success(request, f'Quiz "{quiz.title}" deleted successfully.')
        return redirect('custom_admin:quizzes_list')
    return render(request, 'custom_admin/quizzes/delete.html', {'quiz': quiz})


# ==============================================================================
# QUIZ ATTEMPTS MANAGEMENT VIEWS
# ==============================================================================

@user_passes_test(is_staff_user)
def quiz_attempts_list_view(request):
    """List all quiz attempts"""
    search_query = request.GET.get('search', '')
    attempts = QuizAttempt.objects.select_related(
        'quiz', 'student', 'quiz__module', 'quiz__module__course'
    ).order_by('-started_at')
    
    if search_query:
        attempts = attempts.filter(
            Q(student__name__icontains=search_query) |
            Q(quiz__title__icontains=search_query) |
            Q(quiz__module__course__title__icontains=search_query)
        )
    
    paginator = Paginator(attempts, 25)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'page_obj': page_obj,
        'search_query': search_query,
    }
    
    return render(request, 'custom_admin/quiz_attempts/list.html', context)

@user_passes_test(is_staff_user)
def quiz_attempt_detail_view(request, attempt_id):
    """View quiz attempt details"""
    attempt = get_object_or_404(QuizAttempt, id=attempt_id)
    answers = QuizAnswer.objects.filter(attempt=attempt).select_related(
        'question', 'selected_choice'
    ).order_by('question__order')
    
    # Get student's other attempts for this quiz
    student_attempts = QuizAttempt.objects.filter(
        quiz=attempt.quiz, 
        student=attempt.student,
        completed=True
    ).order_by('-completed_at')
    
    # Calculate best score
    student_best_score = None
    if student_attempts.exists():
        student_best_score = max([a.score_percentage for a in student_attempts])
    
    context = {
        'attempt': attempt,
        'answers': answers,
        'student_attempts': student_attempts,
        'student_best_score': student_best_score,
    }
    
    return render(request, 'custom_admin/quiz_attempts/detail.html', context)


# ==============================================================================
# MODULE PROGRESS MANAGEMENT VIEWS  
# ==============================================================================

@user_passes_test(is_staff_user)
def module_progress_list_view(request):
    """List module progress"""
    search_query = request.GET.get('search', '')
    progress = ModuleProgress.objects.select_related(
        'student', 'module', 'module__course'
    ).order_by('-updated_at')
    
    if search_query:
        progress = progress.filter(
            Q(student__name__icontains=search_query) |
            Q(module__title__icontains=search_query) |
            Q(module__course__title__icontains=search_query)
        )
    
    paginator = Paginator(progress, 25)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'page_obj': page_obj,
        'search_query': search_query,
    }
    
    return render(request, 'custom_admin/module_progress/list.html', context)

@user_passes_test(is_staff_user)
def module_progress_detail_view(request, progress_id):
    """View module progress details"""
    progress = get_object_or_404(ModuleProgress, id=progress_id)
    
    # Get detailed progress information
    assignment_submissions = AssignmentSubmission.objects.filter(
        assignment__module=progress.module,
        student=progress.student
    ).select_related('assignment')
    
    quiz_attempts = QuizAttempt.objects.filter(
        quiz__module=progress.module,
        student=progress.student
    ).select_related('quiz').order_by('-started_at')
    
    context = {
        'progress': progress,
        'assignment_submissions': assignment_submissions,
        'quiz_attempts': quiz_attempts,
    }
    
    return render(request, 'custom_admin/module_progress/detail.html', context)


# ==============================================================================
# AJAX ENDPOINTS
# ==============================================================================

@user_passes_test(is_staff_user)
def get_course_info(request, course_id):
    """AJAX endpoint to get course pricing information"""
    try:
        course = get_object_or_404(Course, id=course_id)
        return JsonResponse({
            'is_free': course.is_free_course,
            'base_price': float(course.price or 0),
            'total_price': float(course.total_price),
            'tax_amount': float(course.tax_amount),
            'course_title': course.title
        })
    except Course.DoesNotExist:
        return JsonResponse({'error': 'Course not found'}, status=404)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


# ==============================================================================
# QUIZ QUESTIONS MANAGEMENT VIEWS
# ==============================================================================

@user_passes_test(is_staff_user)
def quiz_questions_list_view(request):
    """List all quiz questions"""
    search_query = request.GET.get('search', '')
    quiz_id = request.GET.get('quiz')
    
    questions = QuizQuestion.objects.select_related('quiz', 'quiz__module', 'quiz__module__course').prefetch_related('choices').order_by('quiz__title', 'order')
    
    if quiz_id:
        questions = questions.filter(quiz_id=quiz_id)
    
    if search_query:
        questions = questions.filter(
            Q(question_text__icontains=search_query) |
            Q(quiz__title__icontains=search_query) |
            Q(quiz__module__course__title__icontains=search_query)
        )
    
    paginator = Paginator(questions, 25)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    # Get all quizzes for filter dropdown
    quizzes = Quiz.objects.select_related('module', 'module__course').order_by('module__course__title', 'title')
    
    context = {
        'page_obj': page_obj,
        'search_query': search_query,
        'quiz_id': quiz_id,
        'quizzes': quizzes,
    }
    
    return render(request, 'custom_admin/quiz_questions/list.html', context)

@user_passes_test(is_staff_user)
def quiz_question_detail_view(request, question_id):
    """View quiz question details"""
    question = get_object_or_404(QuizQuestion, id=question_id)
    choices = QuizChoice.objects.filter(question=question).order_by('order')
    
    context = {
        'question': question,
        'choices': choices,
    }
    
    return render(request, 'custom_admin/quiz_questions/detail.html', context)

@user_passes_test(is_staff_user)
def quiz_question_create_view(request):
    """Create quiz question with choices"""
    quiz_id = request.GET.get('quiz')
    
    if request.method == 'POST':
        form = CustomQuizQuestionWithChoicesForm(request.POST)
        if form.is_valid():
            question = form.save()
            messages.success(request, f'Quiz question created successfully with answer choices.')
            return redirect('custom_admin:quiz_question_detail', question_id=question.id)
    else:
        initial_data = {}
        if quiz_id:
            try:
                quiz = Quiz.objects.get(id=quiz_id)
                initial_data['quiz'] = quiz
                # Set next order number
                last_question = QuizQuestion.objects.filter(quiz=quiz).order_by('-order').first()
                initial_data['order'] = (last_question.order + 1) if last_question else 1
            except Quiz.DoesNotExist:
                pass
        
        form = CustomQuizQuestionWithChoicesForm(initial=initial_data)
    
    return render(request, 'custom_admin/quiz_questions/form_with_choices.html', {
        'form': form,
        'title': 'Add Quiz Question',
        'is_edit': False,
    })

@user_passes_test(is_staff_user)
def quiz_question_edit_view(request, question_id):
    """Edit quiz question"""
    question = get_object_or_404(QuizQuestion, id=question_id)
    
    if request.method == 'POST':
        form = CustomQuizQuestionForm(request.POST, instance=question)
        if form.is_valid():
            question = form.save()
            messages.success(request, f'Quiz question updated successfully.')
            return redirect('custom_admin:quiz_question_detail', question_id=question.id)
    else:
        form = CustomQuizQuestionForm(instance=question)
    
    return render(request, 'custom_admin/quiz_questions/form.html', {
        'form': form,
        'question': question,
        'title': 'Edit Quiz Question',
        'is_edit': True,
    })

@user_passes_test(is_staff_user)
def quiz_question_delete_view(request, question_id):
    """Delete quiz question"""
    question = get_object_or_404(QuizQuestion, id=question_id)
    if request.method == 'POST':
        question.delete()
        messages.success(request, f'Quiz question deleted successfully.')
        return redirect('custom_admin:quiz_questions_list')
    return render(request, 'custom_admin/quiz_questions/delete.html', {'question': question})


# ==============================================================================
# QUIZ CHOICES MANAGEMENT VIEWS
# ==============================================================================

@user_passes_test(is_staff_user)
def quiz_choices_list_view(request):
    """List all quiz choices"""
    search_query = request.GET.get('search', '')
    question_id = request.GET.get('question')
    
    choices = QuizChoice.objects.select_related('question', 'question__quiz').order_by('question__quiz__title', 'question__order', 'order')
    
    if question_id:
        choices = choices.filter(question_id=question_id)
    
    if search_query:
        choices = choices.filter(
            Q(choice_text__icontains=search_query) |
            Q(question__question_text__icontains=search_query) |
            Q(question__quiz__title__icontains=search_query)
        )
    
    paginator = Paginator(choices, 25)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    # Get all questions for filter dropdown
    questions = QuizQuestion.objects.select_related('quiz').order_by('quiz__title', 'order')
    
    context = {
        'page_obj': page_obj,
        'search_query': search_query,
        'question_id': question_id,
        'questions': questions,
    }
    
    return render(request, 'custom_admin/quiz_choices/list.html', context)

@user_passes_test(is_staff_user)
def quiz_choice_create_view(request):
    """Create quiz choice"""
    question_id = request.GET.get('question')
    
    if request.method == 'POST':
        form = CustomQuizChoiceForm(request.POST)
        if form.is_valid():
            choice = form.save()
            messages.success(request, f'Quiz choice created successfully.')
            return redirect('custom_admin:quiz_question_detail', question_id=choice.question.id)
    else:
        initial_data = {}
        if question_id:
            try:
                question = QuizQuestion.objects.get(id=question_id)
                initial_data['question'] = question
                # Set next order number
                last_choice = QuizChoice.objects.filter(question=question).order_by('-order').first()
                initial_data['order'] = (last_choice.order + 1) if last_choice else 1
            except QuizQuestion.DoesNotExist:
                pass
        
        form = CustomQuizChoiceForm(initial=initial_data)
    
    return render(request, 'custom_admin/quiz_choices/form.html', {
        'form': form,
        'title': 'Add Quiz Choice',
        'is_edit': False,
    })

@user_passes_test(is_staff_user)
def quiz_choice_edit_view(request, choice_id):
    """Edit quiz choice"""
    choice = get_object_or_404(QuizChoice, id=choice_id)
    
    if request.method == 'POST':
        form = CustomQuizChoiceForm(request.POST, instance=choice)
        if form.is_valid():
            choice = form.save()
            messages.success(request, f'Quiz choice updated successfully.')
            return redirect('custom_admin:quiz_question_detail', question_id=choice.question.id)
    else:
        form = CustomQuizChoiceForm(instance=choice)
    
    return render(request, 'custom_admin/quiz_choices/form.html', {
        'form': form,
        'choice': choice,
        'title': 'Edit Quiz Choice',
        'is_edit': True,
    })

@user_passes_test(is_staff_user)
def quiz_choice_delete_view(request, choice_id):
    """Delete quiz choice"""
    choice = get_object_or_404(QuizChoice, id=choice_id)
    question_id = choice.question.id
    if request.method == 'POST':
        choice.delete()
        messages.success(request, f'Quiz choice deleted successfully.')
        return redirect('custom_admin:quiz_question_detail', question_id=question_id)
    return render(request, 'custom_admin/quiz_choices/delete.html', {'choice': choice})

@user_passes_test(is_staff_user)
def get_enrollment_info(request, enrollment_id):
    """AJAX endpoint to get enrollment information for installment plans"""
    try:
        enrollment = get_object_or_404(Enrollment.objects.select_related('user', 'course'), id=enrollment_id)
        return JsonResponse({
            'user_name': enrollment.user.name,
            'course_title': enrollment.course.title,
            'total_amount': float(enrollment.total_amount),
            'outstanding_amount': float(enrollment.outstanding_amount),
            'payment_status': enrollment.payment_status,
            'enrollment_type': enrollment.enrollment_type
        })
    except Enrollment.DoesNotExist:
        return JsonResponse({'error': 'Enrollment not found'}, status=404)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


# ==============================================================================
# QUIZ QUESTIONS MANAGEMENT VIEWS
# ==============================================================================

@user_passes_test(is_staff_user)
def quiz_questions_list_view(request):
    """List all quiz questions"""
    search_query = request.GET.get('search', '')
    quiz_id = request.GET.get('quiz')
    
    questions = QuizQuestion.objects.select_related('quiz', 'quiz__module', 'quiz__module__course').prefetch_related('choices').order_by('quiz__title', 'order')
    
    if quiz_id:
        questions = questions.filter(quiz_id=quiz_id)
    
    if search_query:
        questions = questions.filter(
            Q(question_text__icontains=search_query) |
            Q(quiz__title__icontains=search_query) |
            Q(quiz__module__course__title__icontains=search_query)
        )
    
    paginator = Paginator(questions, 25)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    # Get all quizzes for filter dropdown
    quizzes = Quiz.objects.select_related('module', 'module__course').order_by('module__course__title', 'title')
    
    context = {
        'page_obj': page_obj,
        'search_query': search_query,
        'quiz_id': quiz_id,
        'quizzes': quizzes,
    }
    
    return render(request, 'custom_admin/quiz_questions/list.html', context)

@user_passes_test(is_staff_user)
def quiz_question_detail_view(request, question_id):
    """View quiz question details"""
    question = get_object_or_404(QuizQuestion, id=question_id)
    choices = QuizChoice.objects.filter(question=question).order_by('order')
    
    context = {
        'question': question,
        'choices': choices,
    }
    
    return render(request, 'custom_admin/quiz_questions/detail.html', context)

@user_passes_test(is_staff_user)
def quiz_question_create_view(request):
    """Create quiz question with choices"""
    quiz_id = request.GET.get('quiz')
    
    if request.method == 'POST':
        form = CustomQuizQuestionWithChoicesForm(request.POST)
        if form.is_valid():
            question = form.save()
            messages.success(request, f'Quiz question created successfully with answer choices.')
            return redirect('custom_admin:quiz_question_detail', question_id=question.id)
    else:
        initial_data = {}
        if quiz_id:
            try:
                quiz = Quiz.objects.get(id=quiz_id)
                initial_data['quiz'] = quiz
                # Set next order number
                last_question = QuizQuestion.objects.filter(quiz=quiz).order_by('-order').first()
                initial_data['order'] = (last_question.order + 1) if last_question else 1
            except Quiz.DoesNotExist:
                pass
        
        form = CustomQuizQuestionWithChoicesForm(initial=initial_data)
    
    return render(request, 'custom_admin/quiz_questions/form_with_choices.html', {
        'form': form,
        'title': 'Add Quiz Question',
        'is_edit': False,
    })

@user_passes_test(is_staff_user)
def quiz_question_edit_view(request, question_id):
    """Edit quiz question"""
    question = get_object_or_404(QuizQuestion, id=question_id)
    
    if request.method == 'POST':
        form = CustomQuizQuestionForm(request.POST, instance=question)
        if form.is_valid():
            question = form.save()
            messages.success(request, f'Quiz question updated successfully.')
            return redirect('custom_admin:quiz_question_detail', question_id=question.id)
    else:
        form = CustomQuizQuestionForm(instance=question)
    
    return render(request, 'custom_admin/quiz_questions/form.html', {
        'form': form,
        'question': question,
        'title': 'Edit Quiz Question',
        'is_edit': True,
    })

@user_passes_test(is_staff_user)
def quiz_question_delete_view(request, question_id):
    """Delete quiz question"""
    question = get_object_or_404(QuizQuestion, id=question_id)
    if request.method == 'POST':
        question.delete()
        messages.success(request, f'Quiz question deleted successfully.')
        return redirect('custom_admin:quiz_questions_list')
    return render(request, 'custom_admin/quiz_questions/delete.html', {'question': question})


# ==============================================================================
# QUIZ CHOICES MANAGEMENT VIEWS
# ==============================================================================

@user_passes_test(is_staff_user)
def quiz_choices_list_view(request):
    """List all quiz choices"""
    search_query = request.GET.get('search', '')
    question_id = request.GET.get('question')
    
    choices = QuizChoice.objects.select_related('question', 'question__quiz').order_by('question__quiz__title', 'question__order', 'order')
    
    if question_id:
        choices = choices.filter(question_id=question_id)
    
    if search_query:
        choices = choices.filter(
            Q(choice_text__icontains=search_query) |
            Q(question__question_text__icontains=search_query) |
            Q(question__quiz__title__icontains=search_query)
        )
    
    paginator = Paginator(choices, 25)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    # Get all questions for filter dropdown
    questions = QuizQuestion.objects.select_related('quiz').order_by('quiz__title', 'order')
    
    context = {
        'page_obj': page_obj,
        'search_query': search_query,
        'question_id': question_id,
        'questions': questions,
    }
    
    return render(request, 'custom_admin/quiz_choices/list.html', context)

@user_passes_test(is_staff_user)
def quiz_choice_create_view(request):
    """Create quiz choice"""
    question_id = request.GET.get('question')
    
    if request.method == 'POST':
        form = CustomQuizChoiceForm(request.POST)
        if form.is_valid():
            choice = form.save()
            messages.success(request, f'Quiz choice created successfully.')
            return redirect('custom_admin:quiz_question_detail', question_id=choice.question.id)
    else:
        initial_data = {}
        if question_id:
            try:
                question = QuizQuestion.objects.get(id=question_id)
                initial_data['question'] = question
                # Set next order number
                last_choice = QuizChoice.objects.filter(question=question).order_by('-order').first()
                initial_data['order'] = (last_choice.order + 1) if last_choice else 1
            except QuizQuestion.DoesNotExist:
                pass
        
        form = CustomQuizChoiceForm(initial=initial_data)
    
    return render(request, 'custom_admin/quiz_choices/form.html', {
        'form': form,
        'title': 'Add Quiz Choice',
        'is_edit': False,
    })

@user_passes_test(is_staff_user)
def quiz_choice_edit_view(request, choice_id):
    """Edit quiz choice"""
    choice = get_object_or_404(QuizChoice, id=choice_id)
    
    if request.method == 'POST':
        form = CustomQuizChoiceForm(request.POST, instance=choice)
        if form.is_valid():
            choice = form.save()
            messages.success(request, f'Quiz choice updated successfully.')
            return redirect('custom_admin:quiz_question_detail', question_id=choice.question.id)
    else:
        form = CustomQuizChoiceForm(instance=choice)
    
    return render(request, 'custom_admin/quiz_choices/form.html', {
        'form': form,
        'choice': choice,
        'title': 'Edit Quiz Choice',
        'is_edit': True,
    })

@user_passes_test(is_staff_user)
def quiz_choice_delete_view(request, choice_id):
    """Delete quiz choice"""
    choice = get_object_or_404(QuizChoice, id=choice_id)
    question_id = choice.question.id
    if request.method == 'POST':
        choice.delete()
        messages.success(request, f'Quiz choice deleted successfully.')
        return redirect('custom_admin:quiz_question_detail', question_id=question_id)
    return render(request, 'custom_admin/quiz_choices/delete.html', {'choice': choice})

# VIDEO LESSON ENHANCED VIEWS

@user_passes_test(is_staff_user)
def video_fetch_metadata_view(request):
    """AJAX endpoint to fetch video metadata from APIs"""
    if request.method != 'POST':
        return JsonResponse({'error': 'POST method required'}, status=405)
    
    try:
        import json
        data = json.loads(request.body)
        url = data.get('url', '').strip()
        
        if not url:
            return JsonResponse({'error': 'URL is required'}, status=400)
        
        # Import video service
        from apps.courses.services import VideoIntegrationService
        
        # Fetch metadata
        metadata = VideoIntegrationService.fetch_video_metadata(url)
        
        return JsonResponse(metadata)
        
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON data'}, status=400)
    except Exception as e:
        return JsonResponse({'error': f'Server error: {str(e)}'}, status=500)


@user_passes_test(is_staff_user)
def video_sync_metadata_view(request, lesson_id):
    """AJAX endpoint to sync video metadata from API"""
    if request.method != 'POST':
        return JsonResponse({'error': 'POST method required'}, status=405)
    
    try:
        from apps.courses.models import VideoLesson
        
        video = get_object_or_404(VideoLesson, id=lesson_id)
        
        # Attempt to sync from API
        success, message = video.sync_from_api()
        
        if success:
            video.save()
            return JsonResponse({
                'success': True,
                'message': message,
                'data': {
                    'title': video.title,
                    'description': video.description,
                    'thumbnail_url': video.thumbnail_url,
                    'duration': video.duration,
                    'platform': video.platform,
                    'auto_fetched': video.auto_fetched,
                    'last_sync': video.last_api_sync.isoformat() if video.last_api_sync else None
                }
            })
        else:
            return JsonResponse({'success': False, 'error': message}, status=400)
            
    except Exception as e:
        return JsonResponse({'success': False, 'error': f'Server error: {str(e)}'}, status=500)
