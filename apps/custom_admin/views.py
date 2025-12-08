import json
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import user_passes_test
from django.contrib.auth import authenticate, login, logout
from django.contrib import messages
from django.db.models import Count, Sum
from django.utils import timezone
from datetime import datetime, timedelta
from django.core.paginator import Paginator, PageNotAnInteger, EmptyPage
from django.db.models import Q
from django.urls import reverse
from django.http import JsonResponse

from apps.users.models import User, Team, TeamMembership
from apps.courses.models import (
    Course, Module, VideoLesson, Category,
    Assignment, Quiz, QuizQuestion, QuizChoice, AssignmentSubmission,
    QuizAttempt, QuizAnswer, ModuleProgress, StudentAnalytics, ProgressAlert, MentorSession,
    Certificate
)
from apps.payments.models import Enrollment, Payment, InstallmentPlan, TaxInvoice
from apps.youtube_integration.models import YouTubeVideo, YouTubeChannelConfig
from apps.notifications.models import Notification, EmailTemplate
from apps.ratings.models import CourseRating, CourseReview, ReviewHelpful
from apps.live_sessions.models import LiveSession, SessionParticipant, SessionResource, SessionAnnouncement
from apps.teachers.models import TeacherProfile
from .forms import (CustomVideoLessonForm, CustomAssignmentForm, CustomQuizQuestionForm,
                   CustomQuizChoiceForm, CustomQuizQuestionWithChoicesForm, CustomLiveSessionForm,
                   SessionParticipantForm, BulkAssignParticipantsForm, SessionAnnouncementForm)
from .quiz_reset_views import quiz_attempt_reset_view, quiz_attempt_delete_view


def is_staff_user(user):
    """Check if user has staff-level access (staff, superuser, teacher, or admin role)"""
    if not user.is_authenticated:
        return False
    if user.is_staff or user.is_superuser:
        return True
    # Allow teachers and admin role users to access
    user_role = getattr(user, 'role', None)
    return user_role in ['teacher', 'admin']


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
    """View course details with module management"""
    from apps.courses.models import CourseModule

    course = get_object_or_404(Course, id=course_id)

    # Get modules through CourseModule for proper ordering
    course_modules = CourseModule.objects.filter(
        course=course
    ).select_related('module').prefetch_related(
        'module__video_links__video_lesson',
        'module__assignment_links__assignment',
        'module__quiz_links__quiz'
    ).order_by('order')

    # Extract modules and attach metadata
    modules = []
    for cm in course_modules:
        module = cm.module
        module.course_order = cm.order
        module.course_module_id = cm.id  # For editing/deleting

        # Count content through the many-to-many relationships
        module.videos_count = module.video_links.count()
        module.assignments_count = module.assignment_links.count()
        module.quizzes_count = module.quiz_links.count()

        modules.append(module)

    # Get all modules not yet assigned to this course
    assigned_module_ids = [m.id for m in modules]
    available_modules = Module.objects.exclude(id__in=assigned_module_ids).order_by('title')

    enrollments = Enrollment.objects.filter(course=course).select_related('user', 'team')

    # Get course-level assignments, quizzes, and PDFs
    from apps.courses.models import CourseAssignment, CourseQuiz, CoursePDF, Assignment, Quiz, PDFNote

    course_assignments = CourseAssignment.objects.filter(
        course=course
    ).select_related('assignment').order_by('order')

    course_quizzes = CourseQuiz.objects.filter(
        course=course
    ).select_related('quiz').order_by('order')

    course_pdfs = CoursePDF.objects.filter(
        course=course
    ).select_related('pdf_note').order_by('order')

    # Get available content to add
    assigned_assignment_ids = [ca.assignment.id for ca in course_assignments]
    assigned_quiz_ids = [cq.quiz.id for cq in course_quizzes]
    assigned_pdf_ids = [cp.pdf_note.id for cp in course_pdfs]

    available_assignments = Assignment.objects.exclude(id__in=assigned_assignment_ids).order_by('title')
    available_quizzes = Quiz.objects.exclude(id__in=assigned_quiz_ids).order_by('title')
    available_pdfs = PDFNote.objects.exclude(id__in=assigned_pdf_ids).order_by('title')

    context = {
        'course': course,
        'modules': modules,
        'available_modules': available_modules,
        'enrollments': enrollments,
        'course_assignments': course_assignments,
        'course_quizzes': course_quizzes,
        'course_pdfs': course_pdfs,
        'available_assignments': available_assignments,
        'available_quizzes': available_quizzes,
        'available_pdfs': available_pdfs,
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
    teachers = TeacherProfile.objects.filter(is_active=True).select_related('user').order_by('user__name')

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
            teacher_id = request.POST.get('teacher')

            # Validate required fields
            if not all([title, description, category_id]):
                messages.error(request, 'Please fill in all required fields.')
                return render(request, 'custom_admin/courses/form.html', {
                    'title': 'Add Course',
                    'is_edit': False,
                    'categories': categories,
                    'teachers': teachers
                })

            # Get category
            category = get_object_or_404(Category, id=category_id)

            # Get teacher if selected
            teacher = None
            if teacher_id:
                teacher = TeacherProfile.objects.filter(id=teacher_id).first()

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
                teacher=teacher,
                created_by=request.user
            )

            messages.success(request, f'Course "{course.title}" created successfully.')
            return redirect('custom_admin:course_detail', course_id=course.id)

        except Exception as e:
            messages.error(request, f'Error creating course: {str(e)}')

    return render(request, 'custom_admin/courses/form.html', {
        'title': 'Add Course',
        'is_edit': False,
        'categories': categories,
        'teachers': teachers
    })

@user_passes_test(is_staff_user)
def course_edit_view(request, course_id):
    """Edit a course"""
    course = get_object_or_404(Course, id=course_id)
    categories = Category.objects.all()
    teachers = TeacherProfile.objects.filter(is_active=True).select_related('user').order_by('user__name')

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
            teacher_id = request.POST.get('teacher')

            # Validate required fields
            if not all([title, description, category_id]):
                messages.error(request, 'Please fill in all required fields.')
                return render(request, 'custom_admin/courses/form.html', {
                    'course': course,
                    'title': 'Edit Course',
                    'is_edit': True,
                    'categories': categories,
                    'teachers': teachers
                })

            # Get category
            category = get_object_or_404(Category, id=category_id)

            # Get teacher if selected
            teacher = None
            if teacher_id:
                teacher = TeacherProfile.objects.filter(id=teacher_id).first()

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
            course.teacher = teacher

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
        'categories': categories,
        'teachers': teachers
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


@user_passes_test(is_staff_user)
def course_add_module_view(request, course_id):
    """Add a module to a course"""
    from apps.courses.models import CourseModule

    course = get_object_or_404(Course, id=course_id)

    if request.method == 'POST':
        module_id = request.POST.get('module_id')
        order = request.POST.get('order', 1)

        if not module_id:
            messages.error(request, 'Please select a module.')
            return redirect('custom_admin:course_detail', course_id=course.id)

        module = get_object_or_404(Module, id=module_id)

        # Check if already linked
        if CourseModule.objects.filter(course=course, module=module).exists():
            messages.warning(request, f'Module "{module.title}" is already in this course.')
            return redirect('custom_admin:course_detail', course_id=course.id)

        # Create the link
        CourseModule.objects.create(
            course=course,
            module=module,
            order=int(order)
        )

        messages.success(request, f'Module "{module.title}" added to course successfully.')
        return redirect('custom_admin:course_detail', course_id=course.id)

    return redirect('custom_admin:course_detail', course_id=course.id)


@user_passes_test(is_staff_user)
def course_remove_module_view(request, course_id, course_module_id):
    """Remove a module from a course"""
    from apps.courses.models import CourseModule

    course = get_object_or_404(Course, id=course_id)
    course_module = get_object_or_404(CourseModule, id=course_module_id, course=course)

    if request.method == 'POST':
        module_title = course_module.module.title
        course_module.delete()
        messages.success(request, f'Module "{module_title}" removed from course successfully.')
        return redirect('custom_admin:course_detail', course_id=course.id)

    return render(request, 'custom_admin/courses/remove_module.html', {
        'course': course,
        'course_module': course_module
    })


@user_passes_test(is_staff_user)
def course_add_assignment_view(request, course_id):
    """Add an assignment to a course"""
    from apps.courses.models import CourseAssignment, Assignment

    course = get_object_or_404(Course, id=course_id)

    if request.method == 'POST':
        assignment_id = request.POST.get('assignment_id')
        order = request.POST.get('order', 1)

        if not assignment_id:
            messages.error(request, 'Please select an assignment.')
            return redirect('custom_admin:course_detail', course_id=course.id)

        assignment = get_object_or_404(Assignment, id=assignment_id)

        # Check if already linked
        if CourseAssignment.objects.filter(course=course, assignment=assignment).exists():
            messages.warning(request, f'Assignment "{assignment.title}" is already in this course.')
            return redirect('custom_admin:course_detail', course_id=course.id)

        # Create the link
        CourseAssignment.objects.create(
            course=course,
            assignment=assignment,
            order=int(order)
        )

        messages.success(request, f'Assignment "{assignment.title}" added to course successfully.')
        return redirect('custom_admin:course_detail', course_id=course.id)

    return redirect('custom_admin:course_detail', course_id=course.id)


@user_passes_test(is_staff_user)
def course_remove_assignment_view(request, course_id, course_assignment_id):
    """Remove an assignment from a course"""
    from apps.courses.models import CourseAssignment

    course = get_object_or_404(Course, id=course_id)
    course_assignment = get_object_or_404(CourseAssignment, id=course_assignment_id, course=course)

    if request.method == 'POST':
        assignment_title = course_assignment.assignment.title
        course_assignment.delete()
        messages.success(request, f'Assignment "{assignment_title}" removed from course successfully.')
        return redirect('custom_admin:course_detail', course_id=course.id)

    return redirect('custom_admin:course_detail', course_id=course.id)


@user_passes_test(is_staff_user)
def course_add_quiz_view(request, course_id):
    """Add a quiz to a course"""
    from apps.courses.models import CourseQuiz, Quiz

    course = get_object_or_404(Course, id=course_id)

    if request.method == 'POST':
        quiz_id = request.POST.get('quiz_id')
        order = request.POST.get('order', 1)

        if not quiz_id:
            messages.error(request, 'Please select a quiz.')
            return redirect('custom_admin:course_detail', course_id=course.id)

        quiz = get_object_or_404(Quiz, id=quiz_id)

        # Check if already linked
        if CourseQuiz.objects.filter(course=course, quiz=quiz).exists():
            messages.warning(request, f'Quiz "{quiz.title}" is already in this course.')
            return redirect('custom_admin:course_detail', course_id=course.id)

        # Create the link
        CourseQuiz.objects.create(
            course=course,
            quiz=quiz,
            order=int(order)
        )

        messages.success(request, f'Quiz "{quiz.title}" added to course successfully.')
        return redirect('custom_admin:course_detail', course_id=course.id)

    return redirect('custom_admin:course_detail', course_id=course.id)


@user_passes_test(is_staff_user)
def course_remove_quiz_view(request, course_id, course_quiz_id):
    """Remove a quiz from a course"""
    from apps.courses.models import CourseQuiz

    course = get_object_or_404(Course, id=course_id)
    course_quiz = get_object_or_404(CourseQuiz, id=course_quiz_id, course=course)

    if request.method == 'POST':
        quiz_title = course_quiz.quiz.title
        course_quiz.delete()
        messages.success(request, f'Quiz "{quiz_title}" removed from course successfully.')
        return redirect('custom_admin:course_detail', course_id=course.id)

    return redirect('custom_admin:course_detail', course_id=course.id)


@user_passes_test(is_staff_user)
def course_add_pdf_view(request, course_id):
    """Add a PDF to a course"""
    from apps.courses.models import CoursePDF, PDFNote

    course = get_object_or_404(Course, id=course_id)

    if request.method == 'POST':
        pdf_id = request.POST.get('pdf_id')
        order = request.POST.get('order', 1)

        if not pdf_id:
            messages.error(request, 'Please select a PDF.')
            return redirect('custom_admin:course_detail', course_id=course.id)

        pdf_note = get_object_or_404(PDFNote, id=pdf_id)

        # Check if already linked
        if CoursePDF.objects.filter(course=course, pdf_note=pdf_note).exists():
            messages.warning(request, f'PDF "{pdf_note.title}" is already in this course.')
            return redirect('custom_admin:course_detail', course_id=course.id)

        # Create the link
        CoursePDF.objects.create(
            course=course,
            pdf_note=pdf_note,
            order=int(order)
        )

        messages.success(request, f'PDF "{pdf_note.title}" added to course successfully.')
        return redirect('custom_admin:course_detail', course_id=course.id)

    return redirect('custom_admin:course_detail', course_id=course.id)


@user_passes_test(is_staff_user)
def course_remove_pdf_view(request, course_id, course_pdf_id):
    """Remove a PDF from a course"""
    from apps.courses.models import CoursePDF

    course = get_object_or_404(Course, id=course_id)
    course_pdf = get_object_or_404(CoursePDF, id=course_pdf_id, course=course)

    if request.method == 'POST':
        pdf_title = course_pdf.pdf_note.title
        course_pdf.delete()
        messages.success(request, f'PDF "{pdf_title}" removed from course successfully.')
        return redirect('custom_admin:course_detail', course_id=course.id)

    return redirect('custom_admin:course_detail', course_id=course.id)


@user_passes_test(is_staff_user)
def course_reorder_modules_view(request, course_id):
    """Reorder modules in a course"""
    from apps.courses.models import CourseModule

    course = get_object_or_404(Course, id=course_id)

    if request.method == 'POST':
        # Get the new order from JSON
        new_order = json.loads(request.POST.get('module_order', '[]'))

        # Update order for each module
        for item in new_order:
            CourseModule.objects.filter(
                course=course,
                id=item['course_module_id']
            ).update(order=item['order'])

        messages.success(request, 'Module order updated successfully.')
        return JsonResponse({'success': True})

    return JsonResponse({'error': 'Invalid request'}, status=400)


# ==============================================================================
# MODULES VIEWS
# ==============================================================================

@user_passes_test(is_staff_user)
def modules_list_view(request):
    """List all modules"""
    search_query = request.GET.get('search', '')
    modules = Module.objects.prefetch_related('courses').order_by('title')

    if search_query:
        modules = modules.filter(
            Q(title__icontains=search_query) |
            Q(courses__title__icontains=search_query)
        ).distinct()

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

    # Get related content with ordering
    video_links = module.video_links.select_related('video_lesson').order_by('order')
    assignment_links = module.assignment_links.select_related('assignment').order_by('order')
    quiz_links = module.quiz_links.select_related('quiz').order_by('order')

    # Get courses this module belongs to
    course_links = module.course_links.select_related('course').order_by('order')

    # Get available (not yet assigned) content
    assigned_video_ids = [vl.video_lesson.id for vl in video_links]
    assigned_assignment_ids = [al.assignment.id for al in assignment_links]
    assigned_quiz_ids = [ql.quiz.id for ql in quiz_links]

    available_videos = VideoLesson.objects.exclude(id__in=assigned_video_ids).order_by('title')
    available_assignments = Assignment.objects.exclude(id__in=assigned_assignment_ids).order_by('title')
    available_quizzes = Quiz.objects.exclude(id__in=assigned_quiz_ids).order_by('title')

    # Get module statistics (use first course for stats)
    enrollments_count = 0
    if course_links.exists():
        first_course = course_links.first().course
        enrollments_count = first_course.enrollments.count()

    progress_records = ModuleProgress.objects.filter(module=module)
    completions_count = progress_records.filter(is_completed=True).count()

    context = {
        'module': module,
        'video_links': video_links,
        'assignment_links': assignment_links,
        'quiz_links': quiz_links,
        'course_links': course_links,
        'available_videos': available_videos,
        'available_assignments': available_assignments,
        'available_quizzes': available_quizzes,
        'enrollments_count': enrollments_count,
        'completions_count': completions_count,
        'progress_records': progress_records,
    }

    return render(request, 'custom_admin/modules/detail.html', context)

@user_passes_test(is_staff_user)
def module_create_view(request):
    """Create a new module"""
    from apps.courses.models import CourseModule

    courses = Course.objects.all()

    if request.method == 'POST':
        try:
            # Get form data
            title = request.POST.get('title')
            description = request.POST.get('description')
            course_ids = request.POST.getlist('courses')  # Multiple courses
            order = request.POST.get('order', 1)
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
            if not all([title, description]):
                messages.error(request, 'Please fill in all required fields.')
                return render(request, 'custom_admin/modules/form.html', {
                    'title': 'Add Module',
                    'is_edit': False,
                    'courses': courses
                })

            # Create module (without course relationship)
            module = Module.objects.create(
                title=title,
                description=description,
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

            # Add module to selected courses
            if course_ids:
                for idx, course_id in enumerate(course_ids):
                    course = get_object_or_404(Course, id=course_id)
                    CourseModule.objects.create(
                        course=course,
                        module=module,
                        order=int(order) + idx  # Auto-increment order for multiple courses
                    )

            messages.success(request, f'Module "{module.title}" created successfully and added to {len(course_ids)} course(s).')
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
    from apps.courses.models import CourseModule

    module = get_object_or_404(Module, id=module_id)
    courses = Course.objects.all()
    current_courses = module.courses.all()

    if request.method == 'POST':
        try:
            # Get form data
            title = request.POST.get('title')
            description = request.POST.get('description')
            course_ids = request.POST.getlist('courses')  # Multiple courses
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
            if not all([title, description]):
                messages.error(request, 'Please fill in all required fields.')
                return render(request, 'custom_admin/modules/form.html', {
                    'module': module,
                    'title': 'Edit Module',
                    'is_edit': True,
                    'courses': courses,
                    'current_courses': current_courses
                })

            # Update module
            module.title = title
            module.description = description
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

            # Update course relationships
            # Remove old course links
            module.course_links.all().delete()

            # Add new course links
            if course_ids:
                for idx, course_id in enumerate(course_ids):
                    course = get_object_or_404(Course, id=course_id)
                    # Get next order for this course
                    max_order = CourseModule.objects.filter(course=course).aggregate(
                        models.Max('order')
                    )['order__max'] or 0
                    CourseModule.objects.create(
                        course=course,
                        module=module,
                        order=max_order + 1
                    )

            messages.success(request, f'Module "{module.title}" updated successfully.')
            return redirect('custom_admin:module_detail', module_id=module.id)

        except Exception as e:
            messages.error(request, f'Error updating module: {str(e)}')

    return render(request, 'custom_admin/modules/form.html', {
        'module': module,
        'title': 'Edit Module',
        'is_edit': True,
        'courses': courses,
        'current_courses': current_courses
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
    lessons = VideoLesson.objects.prefetch_related('modules').order_by('title')

    if search_query:
        lessons = lessons.filter(
            Q(title__icontains=search_query) |
            Q(modules__title__icontains=search_query) |
            Q(modules__courses__title__icontains=search_query)
        ).distinct()

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
    from apps.courses.models import ModuleVideo

    if request.method == 'POST':
        form = CustomVideoLessonForm(request.POST, request.FILES)
        module_ids = request.POST.getlist('modules')  # Get selected modules

        if form.is_valid():
            video_lesson = form.save()

            # Add video to selected modules
            if module_ids:
                for idx, module_id in enumerate(module_ids):
                    module = get_object_or_404(Module, id=module_id)
                    # Get next order for this module
                    max_order = ModuleVideo.objects.filter(module=module).aggregate(
                        models.Max('order')
                    )['order__max'] or 0
                    ModuleVideo.objects.create(
                        module=module,
                        video_lesson=video_lesson,
                        order=max_order + 1
                    )

            messages.success(request, f'Video lesson "{video_lesson.title}" created and added to {len(module_ids)} module(s).')
            return redirect('custom_admin:video_lessons_list')
    else:
        form = CustomVideoLessonForm()

    modules = Module.objects.all()
    return render(request, 'custom_admin/video_lessons/form.html', {
        'form': form,
        'title': 'Add Video Lesson',
        'is_edit': False,
        'modules': modules
    })

@user_passes_test(is_staff_user)
def video_lesson_edit_view(request, lesson_id):
    """Edit a video lesson"""
    from apps.courses.models import ModuleVideo

    lesson = get_object_or_404(VideoLesson, id=lesson_id)
    current_modules = lesson.modules.all()

    if request.method == 'POST':
        form = CustomVideoLessonForm(request.POST, request.FILES, instance=lesson)
        module_ids = request.POST.getlist('modules')

        if form.is_valid():
            video_lesson = form.save()

            # Update module relationships
            # Remove old module links
            lesson.module_links.all().delete()

            # Add new module links
            if module_ids:
                for idx, module_id in enumerate(module_ids):
                    module = get_object_or_404(Module, id=module_id)
                    # Get next order for this module
                    max_order = ModuleVideo.objects.filter(module=module).aggregate(
                        models.Max('order')
                    )['order__max'] or 0
                    ModuleVideo.objects.create(
                        module=module,
                        video_lesson=video_lesson,
                        order=max_order + 1
                    )

            messages.success(request, f'Video lesson "{video_lesson.title}" updated successfully.')
            return redirect('custom_admin:video_lessons_list')
    else:
        form = CustomVideoLessonForm(instance=lesson)

    modules = Module.objects.all()
    return render(request, 'custom_admin/video_lessons/form.html', {
        'form': form,
        'lesson': lesson,
        'title': 'Edit Video Lesson',
        'is_edit': True,
        'modules': modules,
        'current_modules': current_modules
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
    search_query = request.GET.get('search', '')
    status_filter = request.GET.get('status', '')

    templates = EmailTemplate.objects.all().order_by('-updated_at')

    if search_query:
        templates = templates.filter(
            Q(name__icontains=search_query) |
            Q(subject__icontains=search_query)
        )

    if status_filter == 'active':
        templates = templates.filter(is_active=True)
    elif status_filter == 'inactive':
        templates = templates.filter(is_active=False)

    paginator = Paginator(templates, 12)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    return render(request, 'custom_admin/email_templates/list.html', {
        'page_obj': page_obj,
        'search_query': search_query
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
    type_filter = request.GET.get('type', '')
    status_filter = request.GET.get('status', '')

    notifications = Notification.objects.select_related('user').order_by('-created_at')

    if search_query:
        notifications = notifications.filter(
            Q(title__icontains=search_query) |
            Q(user__name__icontains=search_query)
        )

    if type_filter:
        notifications = notifications.filter(notification_type=type_filter)

    if status_filter == 'read':
        notifications = notifications.filter(read=True)
    elif status_filter == 'unread':
        notifications = notifications.filter(read=False)

    # Calculate stats
    all_notifications = Notification.objects.all()
    stats = {
        'total': all_notifications.count(),
        'unread': all_notifications.filter(read=False).count(),
        'email_sent': all_notifications.filter(email_sent=True).count(),
        'push_sent': all_notifications.filter(push_sent=True).count(),
    }

    paginator = Paginator(notifications, 25)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    context = {
        'page_obj': page_obj,
        'search_query': search_query,
        'stats': stats,
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


@user_passes_test(is_staff_user)
def users_bulk_delete_view(request):
    """Bulk delete users"""
    if request.method == 'POST':
        user_ids = request.POST.getlist('user_ids')

        if not user_ids:
            messages.error(request, 'No users were selected for deletion.')
            return redirect('custom_admin:users_list')

        try:
            # Get all users to be deleted
            users_to_delete = User.objects.filter(id__in=user_ids)
            deleted_count = users_to_delete.count()

            # Prevent deleting the current user
            if request.user.id in [int(uid) for uid in user_ids]:
                messages.error(request, 'You cannot delete your own account.')
                return redirect('custom_admin:users_list')

            # Prevent deleting superusers (for safety)
            superuser_count = users_to_delete.filter(is_superuser=True).count()
            if superuser_count > 0:
                messages.error(request, 'Cannot delete superuser accounts through bulk delete. Please delete them individually if needed.')
                return redirect('custom_admin:users_list')

            # Delete all selected users
            # Django will handle cascade deletion of related objects (Enrollment, Payment, etc.)
            users_to_delete.delete()

            messages.success(request, f'Successfully deleted {deleted_count} user(s) and all their related data.')

        except Exception as e:
            messages.error(request, f'An error occurred while deleting users: {str(e)}')

        return redirect('custom_admin:users_list')

    # If GET request, redirect back to users list
    return redirect('custom_admin:users_list')


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
    assignments = Assignment.objects.prefetch_related('modules').order_by('title')

    if search_query:
        assignments = assignments.filter(
            Q(title__icontains=search_query) |
            Q(modules__title__icontains=search_query) |
            Q(modules__courses__title__icontains=search_query)
        ).distinct()

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
    module_links = assignment.module_links.select_related('module').order_by('order')

    context = {
        'assignment': assignment,
        'submissions': submissions,
        'module_links': module_links,
    }

    return render(request, 'custom_admin/assignments/detail.html', context)

@user_passes_test(is_staff_user)
def assignment_create_view(request):
    """Create assignment"""
    from apps.courses.models import ModuleAssignment

    if request.method == 'POST':
        form = CustomAssignmentForm(request.POST)
        module_ids = request.POST.getlist('modules')

        if form.is_valid():
            assignment = form.save()

            # Add assignment to selected modules
            if module_ids:
                for module_id in module_ids:
                    module = get_object_or_404(Module, id=module_id)
                    max_order = ModuleAssignment.objects.filter(module=module).aggregate(
                        models.Max('order')
                    )['order__max'] or 0
                    ModuleAssignment.objects.create(
                        module=module,
                        assignment=assignment,
                        order=max_order + 1
                    )

            messages.success(request, f'Assignment "{assignment.title}" created and added to {len(module_ids)} module(s).')
            return redirect('custom_admin:assignments_list')
    else:
        form = CustomAssignmentForm()

    modules = Module.objects.all()
    return render(request, 'custom_admin/assignments/form.html', {
        'form': form,
        'title': 'Add Assignment',
        'is_edit': False,
        'modules': modules
    })

@user_passes_test(is_staff_user)
def assignment_edit_view(request, assignment_id):
    """Edit assignment"""
    from apps.courses.models import ModuleAssignment

    assignment = get_object_or_404(Assignment, id=assignment_id)
    current_modules = assignment.modules.all()

    if request.method == 'POST':
        form = CustomAssignmentForm(request.POST, instance=assignment)
        module_ids = request.POST.getlist('modules')

        if form.is_valid():
            assignment = form.save()

            # Update module relationships
            assignment.module_links.all().delete()

            # Add new module links
            if module_ids:
                for module_id in module_ids:
                    module = get_object_or_404(Module, id=module_id)
                    max_order = ModuleAssignment.objects.filter(module=module).aggregate(
                        models.Max('order')
                    )['order__max'] or 0
                    ModuleAssignment.objects.create(
                        module=module,
                        assignment=assignment,
                        order=max_order + 1
                    )

            messages.success(request, f'Assignment "{assignment.title}" updated successfully.')
            return redirect('custom_admin:assignments_list')
    else:
        form = CustomAssignmentForm(instance=assignment)

    modules = Module.objects.all()
    return render(request, 'custom_admin/assignments/form.html', {
        'form': form,
        'assignment': assignment,
        'title': 'Edit Assignment',
        'is_edit': True,
        'modules': modules,
        'current_modules': current_modules
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
        'assignment', 'student'
    ).prefetch_related('assignment__modules').order_by('-submitted_at')
    
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
    quizzes = Quiz.objects.prefetch_related('modules').annotate(
        questions_count=Count('questions'),
        attempts_count=Count('attempts')
    ).order_by('title')

    if search_query:
        quizzes = quizzes.filter(
            Q(title__icontains=search_query) |
            Q(modules__title__icontains=search_query) |
            Q(modules__courses__title__icontains=search_query)
        ).distinct()

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
    module_links = quiz.module_links.select_related('module').order_by('order')

    context = {
        'quiz': quiz,
        'questions': questions,
        'recent_attempts': attempts,
        'module_links': module_links,
    }

    return render(request, 'custom_admin/quizzes/detail.html', context)

@user_passes_test(is_staff_user)
def quiz_create_view(request):
    """Create quiz"""
    from apps.courses.models import ModuleQuiz

    if request.method == 'POST':
        try:
            # Get form data
            title = request.POST.get('title')
            description = request.POST.get('description')
            module_ids = request.POST.getlist('modules')
            time_limit = request.POST.get('time_limit')
            max_attempts = request.POST.get('max_attempts')
            passing_score = request.POST.get('passing_score', 70)
            is_required = request.POST.get('is_required') == 'on'
            show_results_immediately = request.POST.get('show_results_immediately') == 'on'
            randomize_questions = request.POST.get('randomize_questions') == 'on'

            # Validate required fields
            if not all([title, description]):
                messages.error(request, 'Please fill in all required fields.')
                return render(request, 'custom_admin/quizzes/form.html', {
                    'title': 'Add Quiz',
                    'is_edit': False,
                    'modules': Module.objects.all()
                })

            # Create quiz
            quiz = Quiz.objects.create(
                title=title,
                description=description,
                time_limit=int(time_limit) if time_limit else 30,
                max_attempts=int(max_attempts) if max_attempts else 3,
                passing_score=int(passing_score),
                is_required=is_required,
                show_results_immediately=show_results_immediately,
                randomize_questions=randomize_questions
            )

            # Add quiz to selected modules
            if module_ids:
                for module_id in module_ids:
                    module = get_object_or_404(Module, id=module_id)
                    max_order = ModuleQuiz.objects.filter(module=module).aggregate(
                        models.Max('order')
                    )['order__max'] or 0
                    ModuleQuiz.objects.create(
                        module=module,
                        quiz=quiz,
                        order=max_order + 1
                    )

            messages.success(request, f'Quiz "{quiz.title}" created and added to {len(module_ids)} module(s).')
            return redirect('custom_admin:quiz_detail', quiz_id=quiz.id)

        except Exception as e:
            messages.error(request, f'Error creating quiz: {str(e)}')

    modules = Module.objects.all()
    return render(request, 'custom_admin/quizzes/form.html', {
        'title': 'Add Quiz',
        'is_edit': False,
        'modules': modules
    })

@user_passes_test(is_staff_user)
def quiz_edit_view(request, quiz_id):
    """Edit quiz"""
    from apps.courses.models import ModuleQuiz

    quiz = get_object_or_404(Quiz, id=quiz_id)
    current_modules = quiz.modules.all()

    if request.method == 'POST':
        try:
            # Get form data
            title = request.POST.get('title')
            description = request.POST.get('description')
            module_ids = request.POST.getlist('modules')
            time_limit = request.POST.get('time_limit')
            max_attempts = request.POST.get('max_attempts')
            passing_score = request.POST.get('passing_score', 70)
            is_required = request.POST.get('is_required') == 'on'
            show_results_immediately = request.POST.get('show_results_immediately') == 'on'
            randomize_questions = request.POST.get('randomize_questions') == 'on'

            # Validate required fields
            if not all([title, description]):
                messages.error(request, 'Please fill in all required fields.')
                return render(request, 'custom_admin/quizzes/form.html', {
                    'quiz': quiz,
                    'title': 'Edit Quiz',
                    'is_edit': True,
                    'modules': Module.objects.all(),
                    'current_modules': current_modules
                })

            # Update quiz fields
            quiz.title = title
            quiz.description = description
            quiz.time_limit = int(time_limit) if time_limit else 30
            quiz.max_attempts = int(max_attempts) if max_attempts else 3
            quiz.passing_score = int(passing_score)
            quiz.is_required = is_required
            quiz.show_results_immediately = show_results_immediately
            quiz.randomize_questions = randomize_questions
            quiz.save()

            # Update module relationships
            quiz.module_links.all().delete()

            # Add new module links
            if module_ids:
                for module_id in module_ids:
                    module = get_object_or_404(Module, id=module_id)
                    max_order = ModuleQuiz.objects.filter(module=module).aggregate(
                        models.Max('order')
                    )['order__max'] or 0
                    ModuleQuiz.objects.create(
                        module=module,
                        quiz=quiz,
                        order=max_order + 1
                    )

            messages.success(request, f'Quiz "{quiz.title}" updated successfully.')
            return redirect('custom_admin:quiz_detail', quiz_id=quiz.id)

        except Exception as e:
            messages.error(request, f'Error updating quiz: {str(e)}')

    modules = Module.objects.all()
    return render(request, 'custom_admin/quizzes/form.html', {
        'quiz': quiz,
        'title': 'Edit Quiz',
        'is_edit': True,
        'modules': modules,
        'current_modules': current_modules
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
        'quiz', 'student'
    ).prefetch_related('quiz__modules').order_by('-started_at')
    
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
        'student', 'module'
    ).prefetch_related('module__course_links').order_by('-updated_at')

    if search_query:
        progress = progress.filter(
            Q(student__name__icontains=search_query) |
            Q(module__title__icontains=search_query) |
            Q(module__course_links__title__icontains=search_query)
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


# =====================================
# LIVE SESSIONS VIEWS
# =====================================

@user_passes_test(is_staff_user)
def live_sessions_list_view(request):
    """List all live sessions"""
    query = request.GET.get('q', '')
    status_filter = request.GET.get('status', '')
    course_filter = request.GET.get('course', '')

    sessions = LiveSession.objects.select_related('course', 'created_by').all()

    if query:
        sessions = sessions.filter(
            Q(title__icontains=query) |
            Q(description__icontains=query) |
            Q(course__title__icontains=query)
        )

    if status_filter:
        sessions = sessions.filter(status=status_filter)

    if course_filter:
        sessions = sessions.filter(course_id=course_filter)

    sessions = sessions.order_by('-scheduled_date')

    # Pagination
    paginator = Paginator(sessions, 25)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    # Get filter options
    courses = Course.objects.filter(is_published=True).order_by('title')

    context = {
        'sessions': page_obj,
        'query': query,
        'status_filter': status_filter,
        'course_filter': course_filter,
        'courses': courses,
        'status_choices': LiveSession.SESSION_STATUS_CHOICES,
    }
    return render(request, 'custom_admin/live_sessions/list.html', context)


@user_passes_test(is_staff_user)
def live_session_detail_view(request, session_id):
    """View live session details and participants"""
    session = get_object_or_404(LiveSession, id=session_id)
    participants = session.participants.select_related('student').all()
    announcements = session.announcements.select_related('created_by').order_by('-created_at')

    context = {
        'session': session,
        'participants': participants,
        'announcements': announcements,
    }
    return render(request, 'custom_admin/live_sessions/detail.html', context)


@user_passes_test(is_staff_user)
def live_session_create_view(request):
    """Create a new live session"""
    if request.method == 'POST':
        form = CustomLiveSessionForm(request.POST, user=request.user)
        if form.is_valid():
            use_google_meet = form.cleaned_data.get('use_google_meet', False)

            # Create the session
            session = form.save()

            # Create Google Meet if requested
            if use_google_meet:
                try:
                    from system_settings.google_meet_service import GoogleMeetService
                    meet_service = GoogleMeetService(request.user)
                    google_meet = meet_service.create_meet_session(session)

                    if google_meet:
                        messages.success(
                            request,
                            f'Live session "{session.title}" created with Google Meet link!'
                        )
                    else:
                        messages.warning(
                            request,
                            f'Session created but Google Meet link generation failed. Please add manually.'
                        )
                except ValueError as e:
                    messages.warning(request, f'Session created but: {str(e)}')
                except Exception as e:
                    messages.warning(
                        request,
                        f'Session created but Google Meet error: {str(e)}'
                    )
            else:
                messages.success(request, f'Live session "{session.title}" created successfully!')

            # Auto-assign participants based on assignment type
            assignment_type = form.cleaned_data.get('assignment_type')
            if assignment_type == 'course' and form.cleaned_data.get('course'):
                session.assign_course_students(form.cleaned_data['course'])

            return redirect('custom_admin:live_session_detail', session_id=session.id)
    else:
        form = CustomLiveSessionForm(user=request.user)

    # Check if user has Google Workspace connected
    from system_settings.models import GoogleWorkspaceIntegration
    google_connected = GoogleWorkspaceIntegration.objects.filter(
        admin_user=request.user,
        is_active=True
    ).exists()

    context = {
        'form': form,
        'title': 'Create Live Session',
        'google_connected': google_connected,
    }
    return render(request, 'custom_admin/live_sessions/form.html', context)


@user_passes_test(is_staff_user)
def live_session_edit_view(request, session_id):
    """Edit an existing live session"""
    session = get_object_or_404(LiveSession, id=session_id)

    if request.method == 'POST':
        form = CustomLiveSessionForm(request.POST, instance=session, user=request.user)
        if form.is_valid():
            use_google_meet = form.cleaned_data.get('use_google_meet', False)

            # Save the session
            session = form.save()

            # Update Google Meet if session has one
            if use_google_meet and hasattr(session, 'google_meet_info'):
                try:
                    from system_settings.google_meet_service import GoogleMeetService
                    meet_service = GoogleMeetService(request.user)

                    if meet_service.update_meet_session(session):
                        messages.success(
                            request,
                            f'Live session and Google Meet updated successfully!'
                        )
                    else:
                        messages.warning(
                            request,
                            f'Session updated but Google Meet update failed.'
                        )
                except Exception as e:
                    messages.warning(
                        request,
                        f'Session updated but Google Meet error: {str(e)}'
                    )
            elif use_google_meet and not hasattr(session, 'google_meet_info'):
                # Create new Google Meet if requested but doesn't exist
                try:
                    from system_settings.google_meet_service import GoogleMeetService
                    meet_service = GoogleMeetService(request.user)
                    google_meet = meet_service.create_meet_session(session)

                    if google_meet:
                        messages.success(
                            request,
                            f'Session updated and Google Meet link created!'
                        )
                    else:
                        messages.warning(
                            request,
                            f'Session updated but Google Meet creation failed.'
                        )
                except Exception as e:
                    messages.warning(
                        request,
                        f'Session updated but Google Meet error: {str(e)}'
                    )
            else:
                messages.success(request, f'Live session "{session.title}" updated successfully!')

            return redirect('custom_admin:live_session_detail', session_id=session.id)
    else:
        form = CustomLiveSessionForm(instance=session, user=request.user)

    # Check if user has Google Workspace connected
    from system_settings.models import GoogleWorkspaceIntegration
    google_connected = GoogleWorkspaceIntegration.objects.filter(
        admin_user=request.user,
        is_active=True
    ).exists()

    # Check if session has Google Meet
    has_google_meet = hasattr(session, 'google_meet_info')

    context = {
        'form': form,
        'session': session,
        'title': 'Edit Live Session',
        'google_connected': google_connected,
        'has_google_meet': has_google_meet,
    }
    return render(request, 'custom_admin/live_sessions/form.html', context)


@user_passes_test(is_staff_user)
def live_session_delete_view(request, session_id):
    """Delete a live session"""
    session = get_object_or_404(LiveSession, id=session_id)

    if request.method == 'POST':
        title = session.title
        session.delete()
        messages.success(request, f'Live session "{title}" deleted successfully!')
        return redirect('custom_admin:live_sessions_list')

    context = {
        'session': session,
    }
    return render(request, 'custom_admin/live_sessions/delete.html', context)


@user_passes_test(is_staff_user)
def session_manage_participants_view(request, session_id):
    """Manage participants for a live session"""
    session = get_object_or_404(LiveSession, id=session_id)
    participants = session.participants.select_related('student').all()

    # Handle bulk assignment
    if request.method == 'POST' and 'bulk_assign' in request.POST:
        bulk_form = BulkAssignParticipantsForm(request.POST, session=session)
        if bulk_form.is_valid():
            assignment_type = bulk_form.cleaned_data['assignment_type']

            if assignment_type == 'course_students':
                course = bulk_form.cleaned_data['course']
                session.assign_course_students(course)
                messages.success(request, f'Assigned all students from "{course.title}" to the session.')

            elif assignment_type == 'team_members':
                team = bulk_form.cleaned_data['team']
                session.assign_team_members(team)
                messages.success(request, f'Assigned all members from team "{team.name}" to the session.')

            elif assignment_type == 'individual_students':
                students = bulk_form.cleaned_data['students']
                for student in students:
                    session.add_participant(student)
                messages.success(request, f'Assigned {len(students)} students to the session.')

            return redirect('custom_admin:session_manage_participants', session_id=session.id)
    else:
        bulk_form = BulkAssignParticipantsForm(session=session)

    # Handle individual assignment
    if request.method == 'POST' and (request.POST.get('action') == 'add_individual' or 'add_participant' in request.POST):
        print(f"DEBUG: Processing add_participant POST request for session {session.id}")
        participant_form = SessionParticipantForm(request.POST, session=session)
        if participant_form.is_valid():
            print("DEBUG: Form is valid, calling save()")
            try:
                participant = participant_form.save()
                print(f"DEBUG: Form save returned participant {participant}")
                messages.success(request, 'Participant added successfully!')
                return redirect('custom_admin:session_manage_participants', session_id=session.id)
            except Exception as e:
                print(f"DEBUG: Error saving form: {e}")
                messages.error(request, f'Error adding participant: {e}')
        else:
            print(f"DEBUG: Form is invalid: {participant_form.errors}")
            messages.error(request, 'Please correct the form errors.')
    else:
        participant_form = SessionParticipantForm(session=session)

    context = {
        'session': session,
        'participants': participants,
        'bulk_form': bulk_form,
        'participant_form': participant_form,
    }
    return render(request, 'custom_admin/live_sessions/manage_participants.html', context)


@user_passes_test(is_staff_user)
def session_participant_delete_view(request, session_id, participant_id):
    """Remove a participant from a session"""
    session = get_object_or_404(LiveSession, id=session_id)
    participant = get_object_or_404(SessionParticipant, id=participant_id, session=session)

    if request.method == 'POST':
        student_name = participant.student.name
        participant.delete()
        messages.success(request, f'Removed "{student_name}" from the session.')
        return redirect('custom_admin:session_manage_participants', session_id=session.id)

    context = {
        'session': session,
        'participant': participant,
    }
    return render(request, 'custom_admin/live_sessions/participant_delete.html', context)


@user_passes_test(is_staff_user)
def session_start_view(request, session_id):
    """Start a live session"""
    session = get_object_or_404(LiveSession, id=session_id)

    if request.method == 'POST':
        if session.status == 'scheduled':
            session.start_session()
            messages.success(request, f'Session "{session.title}" has been started!')
        else:
            messages.error(request, 'Session cannot be started from its current status.')
        return redirect('custom_admin:live_session_detail', session_id=session.id)

    context = {
        'session': session,
    }
    return render(request, 'custom_admin/live_sessions/start_confirm.html', context)


@user_passes_test(is_staff_user)
def session_end_view(request, session_id):
    """End a live session"""
    session = get_object_or_404(LiveSession, id=session_id)

    if request.method == 'POST':
        if session.status == 'live':
            session.end_session()
            messages.success(request, f'Session "{session.title}" has been ended!')
        else:
            messages.error(request, 'Session cannot be ended from its current status.')
        return redirect('custom_admin:live_session_detail', session_id=session.id)

    context = {
        'session': session,
    }
    return render(request, 'custom_admin/live_sessions/end_confirm.html', context)


@user_passes_test(is_staff_user)
def session_cancel_view(request, session_id):
    """Cancel a live session"""
    session = get_object_or_404(LiveSession, id=session_id)

    if request.method == 'POST':
        if session.status in ['scheduled', 'live']:
            session.cancel_session()
            messages.success(request, f'Session "{session.title}" has been cancelled!')
        else:
            messages.error(request, 'Session cannot be cancelled from its current status.')
        return redirect('custom_admin:live_session_detail', session_id=session.id)

    context = {
        'session': session,
    }
    return render(request, 'custom_admin/live_sessions/cancel_confirm.html', context)


@user_passes_test(is_staff_user)
def session_announcement_create_view(request, session_id):
    """Create an announcement for a session"""
    session = get_object_or_404(LiveSession, id=session_id)

    if request.method == 'POST':
        form = SessionAnnouncementForm(request.POST, session=session, user=request.user)
        if form.is_valid():
            announcement = form.save()
            messages.success(request, 'Announcement created successfully!')
            return redirect('custom_admin:live_session_detail', session_id=session.id)
    else:
        form = SessionAnnouncementForm(session=session, user=request.user)

    context = {
        'form': form,
        'session': session,
        'title': 'Create Announcement',
    }
    return render(request, 'custom_admin/live_sessions/announcement_form.html', context)


# ==============================================================================
# MODULE CONTENT MANAGEMENT VIEWS
# ==============================================================================

@user_passes_test(is_staff_user)
def module_add_video_view(request, module_id):
    """Add a video to a module"""
    from apps.courses.models import ModuleVideo
    module = get_object_or_404(Module, id=module_id)

    if request.method == 'POST':
        video_id = request.POST.get('video_id')
        order = request.POST.get('order', 1)

        if not video_id:
            messages.error(request, 'Please select a video.')
            return redirect('custom_admin:module_detail', module_id=module.id)

        video = get_object_or_404(VideoLesson, id=video_id)

        # Check if already exists
        if ModuleVideo.objects.filter(module=module, video_lesson=video).exists():
            messages.warning(request, f'Video "{video.title}" is already in this module.')
            return redirect('custom_admin:module_detail', module_id=module.id)

        # Create the link
        ModuleVideo.objects.create(
            module=module,
            video_lesson=video,
            order=int(order)
        )

        messages.success(request, f'Video "{video.title}" added to module successfully!')
        return redirect('custom_admin:module_detail', module_id=module.id)

    return redirect('custom_admin:module_detail', module_id=module.id)


@user_passes_test(is_staff_user)
def module_remove_video_view(request, module_id, module_video_id):
    """Remove a video from a module"""
    from apps.courses.models import ModuleVideo
    module = get_object_or_404(Module, id=module_id)
    module_video = get_object_or_404(ModuleVideo, id=module_video_id, module=module)

    if request.method == 'POST':
        video_title = module_video.video_lesson.title
        module_video.delete()
        messages.success(request, f'Video "{video_title}" removed from module successfully!')
        return redirect('custom_admin:module_detail', module_id=module.id)

    return redirect('custom_admin:module_detail', module_id=module.id)


@user_passes_test(is_staff_user)
def module_add_assignment_view(request, module_id):
    """Add an assignment to a module"""
    from apps.courses.models import ModuleAssignment
    module = get_object_or_404(Module, id=module_id)

    if request.method == 'POST':
        assignment_id = request.POST.get('assignment_id')
        order = request.POST.get('order', 1)

        if not assignment_id:
            messages.error(request, 'Please select an assignment.')
            return redirect('custom_admin:module_detail', module_id=module.id)

        assignment = get_object_or_404(Assignment, id=assignment_id)

        # Check if already exists
        if ModuleAssignment.objects.filter(module=module, assignment=assignment).exists():
            messages.warning(request, f'Assignment "{assignment.title}" is already in this module.')
            return redirect('custom_admin:module_detail', module_id=module.id)

        # Create the link
        ModuleAssignment.objects.create(
            module=module,
            assignment=assignment,
            order=int(order)
        )

        messages.success(request, f'Assignment "{assignment.title}" added to module successfully!')
        return redirect('custom_admin:module_detail', module_id=module.id)

    return redirect('custom_admin:module_detail', module_id=module.id)


@user_passes_test(is_staff_user)
def module_remove_assignment_view(request, module_id, module_assignment_id):
    """Remove an assignment from a module"""
    from apps.courses.models import ModuleAssignment
    module = get_object_or_404(Module, id=module_id)
    module_assignment = get_object_or_404(ModuleAssignment, id=module_assignment_id, module=module)

    if request.method == 'POST':
        assignment_title = module_assignment.assignment.title
        module_assignment.delete()
        messages.success(request, f'Assignment "{assignment_title}" removed from module successfully!')
        return redirect('custom_admin:module_detail', module_id=module.id)

    return redirect('custom_admin:module_detail', module_id=module.id)


@user_passes_test(is_staff_user)
def module_add_quiz_view(request, module_id):
    """Add a quiz to a module"""
    from apps.courses.models import ModuleQuiz
    module = get_object_or_404(Module, id=module_id)

    if request.method == 'POST':
        quiz_id = request.POST.get('quiz_id')
        order = request.POST.get('order', 1)

        if not quiz_id:
            messages.error(request, 'Please select a quiz.')
            return redirect('custom_admin:module_detail', module_id=module.id)

        quiz = get_object_or_404(Quiz, id=quiz_id)

        # Check if already exists
        if ModuleQuiz.objects.filter(module=module, quiz=quiz).exists():
            messages.warning(request, f'Quiz "{quiz.title}" is already in this module.')
            return redirect('custom_admin:module_detail', module_id=module.id)

        # Create the link
        ModuleQuiz.objects.create(
            module=module,
            quiz=quiz,
            order=int(order)
        )

        messages.success(request, f'Quiz "{quiz.title}" added to module successfully!')
        return redirect('custom_admin:module_detail', module_id=module.id)

    return redirect('custom_admin:module_detail', module_id=module.id)


@user_passes_test(is_staff_user)
def module_remove_quiz_view(request, module_id, module_quiz_id):
    """Remove a quiz from a module"""
    from apps.courses.models import ModuleQuiz
    module = get_object_or_404(Module, id=module_id)
    module_quiz = get_object_or_404(ModuleQuiz, id=module_quiz_id, module=module)

    if request.method == 'POST':
        quiz_title = module_quiz.quiz.title
        module_quiz.delete()
        messages.success(request, f'Quiz "{quiz_title}" removed from module successfully!')
        return redirect('custom_admin:module_detail', module_id=module.id)

    return redirect('custom_admin:module_detail', module_id=module.id)


@user_passes_test(is_staff_user)
def module_bulk_delete_videos_view(request, module_id):
    """Bulk delete videos from a module"""
    from apps.courses.models import ModuleVideo
    module = get_object_or_404(Module, id=module_id)

    if request.method == 'POST':
        ids = request.POST.get('ids', '')
        if ids:
            id_list = [int(id.strip()) for id in ids.split(',') if id.strip()]
            deleted_count = ModuleVideo.objects.filter(id__in=id_list, module=module).delete()[0]
            messages.success(request, f'Successfully removed {deleted_count} video(s) from module!')
        else:
            messages.error(request, 'No videos selected.')

        return redirect('custom_admin:module_detail', module_id=module.id)

    return redirect('custom_admin:module_detail', module_id=module.id)


@user_passes_test(is_staff_user)
def module_bulk_delete_assignments_view(request, module_id):
    """Bulk delete assignments from a module"""
    from apps.courses.models import ModuleAssignment
    module = get_object_or_404(Module, id=module_id)

    if request.method == 'POST':
        ids = request.POST.get('ids', '')
        if ids:
            id_list = [int(id.strip()) for id in ids.split(',') if id.strip()]
            deleted_count = ModuleAssignment.objects.filter(id__in=id_list, module=module).delete()[0]
            messages.success(request, f'Successfully removed {deleted_count} assignment(s) from module!')
        else:
            messages.error(request, 'No assignments selected.')

        return redirect('custom_admin:module_detail', module_id=module.id)

    return redirect('custom_admin:module_detail', module_id=module.id)


@user_passes_test(is_staff_user)
def module_bulk_delete_quizzes_view(request, module_id):
    """Bulk delete quizzes from a module"""
    from apps.courses.models import ModuleQuiz
    module = get_object_or_404(Module, id=module_id)

    if request.method == 'POST':
        ids = request.POST.get('ids', '')
        if ids:
            id_list = [int(id.strip()) for id in ids.split(',') if id.strip()]
            deleted_count = ModuleQuiz.objects.filter(id__in=id_list, module=module).delete()[0]
            messages.success(request, f'Successfully removed {deleted_count} quiz(zes) from module!')
        else:
            messages.error(request, 'No quizzes selected.')

        return redirect('custom_admin:module_detail', module_id=module.id)

    return redirect('custom_admin:module_detail', module_id=module.id)


@user_passes_test(is_staff_user)
def module_reorder_videos_view(request, module_id):
    """Reorder videos in a module"""
    from apps.courses.models import ModuleVideo

    module = get_object_or_404(Module, id=module_id)

    if request.method == 'POST':
        # Get the new order from JSON
        new_order = json.loads(request.POST.get('video_order', '[]'))

        # Update order for each video
        for item in new_order:
            ModuleVideo.objects.filter(
                module=module,
                id=item['link_id']
            ).update(order=item['order'])

        messages.success(request, 'Video order updated successfully.')
        return JsonResponse({'success': True})

    return JsonResponse({'error': 'Invalid request'}, status=400)


@user_passes_test(is_staff_user)
def module_reorder_assignments_view(request, module_id):
    """Reorder assignments in a module"""
    from apps.courses.models import ModuleAssignment

    module = get_object_or_404(Module, id=module_id)

    if request.method == 'POST':
        # Get the new order from JSON
        new_order = json.loads(request.POST.get('assignment_order', '[]'))

        # Update order for each assignment
        for item in new_order:
            ModuleAssignment.objects.filter(
                module=module,
                id=item['link_id']
            ).update(order=item['order'])

        messages.success(request, 'Assignment order updated successfully.')
        return JsonResponse({'success': True})

    return JsonResponse({'error': 'Invalid request'}, status=400)


@user_passes_test(is_staff_user)
def module_reorder_quizzes_view(request, module_id):
    """Reorder quizzes in a module"""
    from apps.courses.models import ModuleQuiz

    module = get_object_or_404(Module, id=module_id)

    if request.method == 'POST':
        # Get the new order from JSON
        new_order = json.loads(request.POST.get('quiz_order', '[]'))

        # Update order for each quiz
        for item in new_order:
            ModuleQuiz.objects.filter(
                module=module,
                id=item['link_id']
            ).update(order=item['order'])

        messages.success(request, 'Quiz order updated successfully.')
        return JsonResponse({'success': True})

    return JsonResponse({'error': 'Invalid request'}, status=400)


# ==============================================================================
# FEATURE CONFIGURATION VIEW
# ==============================================================================

@user_passes_test(is_staff_user)
def feature_config_view(request):
    """Manage feature toggles for the LMS"""
    from apps.core.models import FeatureConfig
    from django.core.cache import cache

    config = FeatureConfig.get_config()

    if request.method == 'POST':
        # Update config based on form data
        config.enable_online_courses = request.POST.get('online_courses') == 'on'
        config.enable_live_sessions = request.POST.get('live_sessions') == 'on'
        config.enable_online_enrollment = request.POST.get('online_enrollment') == 'on'
        config.enable_certificates = request.POST.get('certificates') == 'on'
        config.enable_tuition_management = request.POST.get('tuition') == 'on'
        config.enable_finance_management = request.POST.get('finance') == 'on'
        config.enable_payments = request.POST.get('payments') == 'on'
        config.enable_assessments = request.POST.get('assessments') == 'on'
        config.enable_notifications = request.POST.get('notifications') == 'on'
        config.enable_website_content = request.POST.get('website_content') == 'on'
        config.enable_youtube_integration = request.POST.get('youtube') == 'on'
        config.enable_analytics = request.POST.get('analytics') == 'on'
        config.updated_by = request.user
        config.save()

        # Clear cache
        cache.delete('feature_config')

        messages.success(request, 'Feature settings updated successfully!')
        return redirect('custom_admin:feature_config')

    context = {
        'config': config,
    }
    return render(request, 'custom_admin/settings/feature_config.html', context)


# ==============================================================================
# SYSTEM SETTINGS MANAGEMENT VIEWS
# ==============================================================================

@user_passes_test(is_staff_user)
def settings_list_view(request):
    """List all system settings grouped by category"""
    from system_settings.models import SystemSetting

    search_query = request.GET.get('search', '')
    category_filter = request.GET.get('category', '')

    settings = SystemSetting.objects.select_related('updated_by').all()

    if search_query:
        settings = settings.filter(
            Q(key__icontains=search_query) |
            Q(description__icontains=search_query)
        )

    if category_filter:
        settings = settings.filter(category=category_filter)

    settings = settings.order_by('category', 'key')

    # Group settings by category
    from collections import defaultdict
    settings_by_category = defaultdict(list)
    for setting in settings:
        settings_by_category[setting.get_category_display()].append(setting)

    # Check if user has Google Workspace connected
    from system_settings.models import GoogleWorkspaceIntegration
    google_integration = GoogleWorkspaceIntegration.objects.filter(
        admin_user=request.user,
        is_active=True
    ).first()

    context = {
        'settings_by_category': dict(settings_by_category),
        'search_query': search_query,
        'category_filter': category_filter,
        'category_choices': SystemSetting.CATEGORY_CHOICES,
        'google_integration': google_integration,
    }

    return render(request, 'custom_admin/settings/list.html', context)


@user_passes_test(is_staff_user)
def setting_create_view(request):
    """Create a new system setting"""
    from system_settings.models import SystemSetting
    from .forms import SystemSettingForm

    if request.method == 'POST':
        form = SystemSettingForm(request.POST)
        if form.is_valid():
            setting = form.save(commit=False)
            setting.updated_by = request.user
            setting.save()

            # Clear cache for this setting
            from django.core.cache import cache
            cache.delete(f'system_setting_{setting.key}')

            messages.success(request, f'Setting "{setting.key}" created successfully.')
            return redirect('custom_admin:settings_list')
    else:
        form = SystemSettingForm()

    context = {
        'form': form,
        'title': 'Add System Setting',
        'is_edit': False,
    }
    return render(request, 'custom_admin/settings/form.html', context)


@user_passes_test(is_staff_user)
def setting_edit_view(request, setting_id):
    """Edit an existing system setting"""
    from system_settings.models import SystemSetting, SettingChangeLog
    from .forms import SystemSettingForm

    setting = get_object_or_404(SystemSetting, id=setting_id)
    old_value = setting.value

    if request.method == 'POST':
        form = SystemSettingForm(request.POST, instance=setting)
        if form.is_valid():
            setting = form.save(commit=False)
            setting.updated_by = request.user
            setting.save()

            # Log the change
            if old_value != setting.value:
                change_reason = request.POST.get('change_reason', '')
                SettingChangeLog.objects.create(
                    setting=setting,
                    changed_by=request.user,
                    old_value=old_value,
                    new_value=setting.value,
                    change_reason=change_reason,
                    ip_address=request.META.get('REMOTE_ADDR'),
                    user_agent=request.META.get('HTTP_USER_AGENT', '')
                )

            # Clear cache for this setting
            from django.core.cache import cache
            cache.delete(f'system_setting_{setting.key}')

            messages.success(request, f'Setting "{setting.key}" updated successfully.')
            return redirect('custom_admin:settings_list')
    else:
        form = SystemSettingForm(instance=setting)

    context = {
        'form': form,
        'setting': setting,
        'title': f'Edit Setting: {setting.key}',
        'is_edit': True,
    }
    return render(request, 'custom_admin/settings/form.html', context)


@user_passes_test(is_staff_user)
def setting_delete_view(request, setting_id):
    """Delete a system setting"""
    from system_settings.models import SystemSetting

    setting = get_object_or_404(SystemSetting, id=setting_id)

    if request.method == 'POST':
        key = setting.key

        # Clear cache
        from django.core.cache import cache
        cache.delete(f'system_setting_{key}')

        setting.delete()
        messages.success(request, f'Setting "{key}" deleted successfully.')
        return redirect('custom_admin:settings_list')

    context = {
        'setting': setting,
    }
    return render(request, 'custom_admin/settings/delete.html', context)


@user_passes_test(is_staff_user)
def setting_history_view(request, setting_id):
    """View change history for a setting"""
    from system_settings.models import SystemSetting, SettingChangeLog

    setting = get_object_or_404(SystemSetting, id=setting_id)
    change_logs = SettingChangeLog.objects.filter(
        setting=setting
    ).select_related('changed_by').order_by('-changed_at')

    paginator = Paginator(change_logs, 25)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    context = {
        'setting': setting,
        'page_obj': page_obj,
    }
    return render(request, 'custom_admin/settings/history.html', context)


@user_passes_test(is_staff_user)
def setting_test_connection_view(request, setting_id):
    """AJAX endpoint to test a setting (e.g., email, payment gateway)"""
    from system_settings.models import SystemSetting

    if request.method != 'POST':
        return JsonResponse({'error': 'POST method required'}, status=405)

    setting = get_object_or_404(SystemSetting, id=setting_id)

    # Test based on category
    try:
        if setting.category == 'email':
            # Test email connection
            from django.core.mail import send_mail
            from django.conf import settings

            send_mail(
                'Test Email from CodeLearn LMS',
                'This is a test email to verify email settings.',
                settings.DEFAULT_FROM_EMAIL,
                [request.user.email],
                fail_silently=False,
            )
            return JsonResponse({
                'success': True,
                'message': f'Test email sent successfully to {request.user.email}'
            })

        elif setting.category == 'payment':
            # Test Razorpay connection
            if 'RAZORPAY' in setting.key:
                import razorpay
                from system_settings.utils import get_setting

                client = razorpay.Client(auth=(
                    get_setting('RAZORPAY_KEY_ID'),
                    get_setting('RAZORPAY_KEY_SECRET')
                ))

                # Try to fetch payment methods (simple API call)
                methods = client.payment.fetch_all()
                return JsonResponse({
                    'success': True,
                    'message': 'Razorpay connection successful!'
                })

        else:
            return JsonResponse({
                'success': False,
                'message': 'Test connection not available for this category'
            })

    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': f'Connection test failed: {str(e)}'
        }, status=400)


# ============================================
# GOOGLE WORKSPACE OAUTH VIEWS
# ============================================

@user_passes_test(is_staff_user)
def google_oauth_initiate_view(request):
    """Initiate Google OAuth flow"""
    from system_settings.google_oauth import GoogleOAuthService

    try:
        oauth_service = GoogleOAuthService(request)
        authorization_url, state = oauth_service.get_authorization_url()

        # Store state in session for verification
        request.session['google_oauth_state'] = state

        return redirect(authorization_url)

    except ValueError as e:
        messages.error(request, str(e))
        return redirect('custom_admin:settings_list')
    except Exception as e:
        messages.error(request, f'Error initiating OAuth: {str(e)}')
        return redirect('custom_admin:settings_list')


@user_passes_test(is_staff_user)
def google_oauth_callback_view(request):
    """Handle Google OAuth callback"""
    from system_settings.google_oauth import GoogleOAuthService

    # Get state from session
    stored_state = request.session.get('google_oauth_state')
    returned_state = request.GET.get('state')

    # Verify state to prevent CSRF
    if not stored_state or stored_state != returned_state:
        messages.error(request, 'OAuth state mismatch. Please try again.')
        return redirect('custom_admin:settings_list')

    # Check for errors
    error = request.GET.get('error')
    if error:
        messages.error(request, f'OAuth authorization failed: {error}')
        return redirect('custom_admin:settings_list')

    try:
        oauth_service = GoogleOAuthService(request)

        # Build authorization response URL
        authorization_response = request.build_absolute_uri()

        # Exchange code for credentials
        credentials_dict = oauth_service.handle_callback(
            authorization_response,
            stored_state
        )

        # Save credentials for user
        integration = oauth_service.save_credentials(request.user, credentials_dict)

        messages.success(
            request,
            f'Successfully connected to Google Workspace as {integration.google_email}'
        )

        # Clean up session
        del request.session['google_oauth_state']

    except Exception as e:
        messages.error(request, f'Error connecting to Google: {str(e)}')

    return redirect('custom_admin:settings_list')


@user_passes_test(is_staff_user)
def google_oauth_disconnect_view(request):
    """Disconnect Google Workspace integration"""
    from system_settings.google_oauth import GoogleOAuthService

    if request.method == 'POST':
        oauth_service = GoogleOAuthService(request)

        if oauth_service.disconnect(request.user):
            messages.success(request, 'Successfully disconnected from Google Workspace')
        else:
            messages.warning(request, 'No Google Workspace connection found')

    return redirect('custom_admin:settings_list')


@user_passes_test(is_staff_user)
def google_oauth_test_view(request):
    """Test Google Calendar API connection"""
    from system_settings.google_oauth import GoogleOAuthService

    oauth_service = GoogleOAuthService(request)
    success, message = oauth_service.test_connection(request.user)

    if success:
        messages.success(request, message)
    else:
        messages.error(request, message)

    return redirect('custom_admin:settings_list')


# ============================================================================
# PDF NOTES VIEWS
# ============================================================================

@user_passes_test(is_staff_user)
def pdf_notes_list_view(request):
    """List all PDF notes with search and filter"""
    from apps.courses.models import PDFNote

    search_query = request.GET.get('search', '')
    pdf_notes = PDFNote.objects.all()

    if search_query:
        pdf_notes = pdf_notes.filter(
            Q(title__icontains=search_query) |
            Q(description__icontains=search_query)
        )

    pdf_notes = pdf_notes.order_by('-created_at')

    # Pagination
    paginator = Paginator(pdf_notes, 25)
    page = request.GET.get('page')
    try:
        pdf_notes = paginator.page(page)
    except PageNotAnInteger:
        pdf_notes = paginator.page(1)
    except EmptyPage:
        pdf_notes = paginator.page(paginator.num_pages)

    context = {
        'pdf_notes': pdf_notes,
        'search_query': search_query,
        'total_count': PDFNote.objects.count()
    }

    return render(request, 'custom_admin/pdf_notes/list.html', context)


@user_passes_test(is_staff_user)
def pdf_note_create_view(request):
    """Create a new PDF note"""
    from apps.courses.models import PDFNote
    from apps.custom_admin.forms import PDFNoteForm

    if request.method == 'POST':
        form = PDFNoteForm(request.POST, request.FILES)
        if form.is_valid():
            pdf_note = form.save()
            messages.success(request, f'PDF note "{pdf_note.title}" created successfully.')
            return redirect('custom_admin:pdf_notes_list')
    else:
        form = PDFNoteForm()

    context = {
        'form': form,
        'is_edit': False
    }

    return render(request, 'custom_admin/pdf_notes/form.html', context)


@user_passes_test(is_staff_user)
def pdf_note_edit_view(request, pdf_id):
    """Edit an existing PDF note"""
    from apps.courses.models import PDFNote
    from apps.custom_admin.forms import PDFNoteForm

    pdf_note = get_object_or_404(PDFNote, id=pdf_id)

    if request.method == 'POST':
        form = PDFNoteForm(request.POST, request.FILES, instance=pdf_note)
        if form.is_valid():
            pdf_note = form.save()
            messages.success(request, f'PDF note "{pdf_note.title}" updated successfully.')
            return redirect('custom_admin:pdf_notes_list')
    else:
        form = PDFNoteForm(instance=pdf_note)

    context = {
        'form': form,
        'pdf_note': pdf_note,
        'is_edit': True
    }

    return render(request, 'custom_admin/pdf_notes/form.html', context)


@user_passes_test(is_staff_user)
def pdf_note_delete_view(request, pdf_id):
    """Delete a PDF note"""
    from apps.courses.models import PDFNote

    pdf_note = get_object_or_404(PDFNote, id=pdf_id)

    if request.method == 'POST':
        title = pdf_note.title
        pdf_note.delete()
        messages.success(request, f'PDF note "{title}" deleted successfully.')
        return redirect('custom_admin:pdf_notes_list')

    return redirect('custom_admin:pdf_notes_list')


# ==========================================
# COURSE ENQUIRIES MANAGEMENT
# ==========================================

@user_passes_test(is_staff_user)
def course_enquiries_list_view(request):
    """List all course enquiries"""
    from apps.content_management.models import CourseEnquiry
    
    search_query = request.GET.get('search', '')
    status_filter = request.GET.get('status', '')
    course_filter = request.GET.get('course', '')
    
    enquiries = CourseEnquiry.objects.select_related('course', 'user', 'assigned_to').order_by('-created_at')
    
    if search_query:
        enquiries = enquiries.filter(
            Q(name__icontains=search_query) |
            Q(email__icontains=search_query) |
            Q(phone__icontains=search_query) |
            Q(course__title__icontains=search_query)
        )
    
    if status_filter:
        enquiries = enquiries.filter(status=status_filter)
    
    if course_filter:
        enquiries = enquiries.filter(course_id=course_filter)
    
    # Get status choices and courses for filters
    status_choices = CourseEnquiry.STATUS_CHOICES
    courses = Course.objects.filter(is_published=True).order_by('title')
    
    # Stats
    total_enquiries = enquiries.count()
    new_enquiries = enquiries.filter(status='new').count()
    contacted_enquiries = enquiries.filter(status='contacted').count()
    enrolled_enquiries = enquiries.filter(status='enrolled').count()
    
    paginator = Paginator(enquiries, 25)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'page_obj': page_obj,
        'search_query': search_query,
        'status_filter': status_filter,
        'course_filter': course_filter,
        'status_choices': status_choices,
        'courses': courses,
        'total_enquiries': total_enquiries,
        'new_enquiries': new_enquiries,
        'contacted_enquiries': contacted_enquiries,
        'enrolled_enquiries': enrolled_enquiries,
    }
    
    return render(request, 'custom_admin/enquiries/list.html', context)


@user_passes_test(is_staff_user)
def course_enquiry_detail_view(request, enquiry_id):
    """View and update enquiry details"""
    from apps.content_management.models import CourseEnquiry
    
    enquiry = get_object_or_404(CourseEnquiry.objects.select_related('course', 'user', 'assigned_to'), id=enquiry_id)
    
    if request.method == 'POST':
        # Update enquiry status and notes
        new_status = request.POST.get('status')
        notes = request.POST.get('notes', '')
        assigned_to_id = request.POST.get('assigned_to')
        
        if new_status:
            enquiry.status = new_status
        enquiry.notes = notes
        
        if assigned_to_id:
            enquiry.assigned_to_id = assigned_to_id
        else:
            enquiry.assigned_to = None
            
        enquiry.save()
        messages.success(request, f'Enquiry from "{enquiry.name}" updated successfully.')
        return redirect('custom_admin:course_enquiry_detail', enquiry_id=enquiry.id)
    
    # Get staff users for assignment
    staff_users = User.objects.filter(is_staff=True).order_by('first_name', 'username')
    status_choices = CourseEnquiry.STATUS_CHOICES
    
    context = {
        'enquiry': enquiry,
        'staff_users': staff_users,
        'status_choices': status_choices,
    }
    
    return render(request, 'custom_admin/enquiries/detail.html', context)


@user_passes_test(is_staff_user)
def course_enquiry_delete_view(request, enquiry_id):
    """Delete an enquiry"""
    from apps.content_management.models import CourseEnquiry

    enquiry = get_object_or_404(CourseEnquiry, id=enquiry_id)

    if request.method == 'POST':
        name = enquiry.name
        enquiry.delete()
        messages.success(request, f'Enquiry from "{name}" deleted successfully.')
        return redirect('custom_admin:course_enquiries_list')

    return redirect('custom_admin:course_enquiries_list')


# ==============================================================================
# CERTIFICATE VIEWS
# ==============================================================================

@user_passes_test(is_staff_user)
def certificates_list_view(request):
    """List all certificates with search and filters"""
    search_query = request.GET.get('search', '')
    status_filter = request.GET.get('status', '')
    course_filter = request.GET.get('course', '')

    certificates = Certificate.objects.select_related('student', 'course').order_by('-issue_date')

    if search_query:
        certificates = certificates.filter(
            Q(certificate_number__icontains=search_query) |
            Q(student__name__icontains=search_query) |
            Q(student__email__icontains=search_query) |
            Q(course__title__icontains=search_query)
        )

    if status_filter == 'valid':
        certificates = certificates.filter(is_revoked=False)
    elif status_filter == 'revoked':
        certificates = certificates.filter(is_revoked=True)

    if course_filter:
        certificates = certificates.filter(course_id=course_filter)

    # Stats
    all_certs = Certificate.objects.all()
    stats = {
        'total': all_certs.count(),
        'valid': all_certs.filter(is_revoked=False).count(),
        'revoked': all_certs.filter(is_revoked=True).count(),
        'this_month': all_certs.filter(issue_date__month=timezone.now().month, issue_date__year=timezone.now().year).count(),
    }

    # Get courses for filter dropdown
    courses = Course.objects.filter(is_published=True).order_by('title')

    paginator = Paginator(certificates, 25)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    context = {
        'page_obj': page_obj,
        'search_query': search_query,
        'stats': stats,
        'courses': courses,
    }

    return render(request, 'custom_admin/certificates/list.html', context)


@user_passes_test(is_staff_user)
def certificate_create_view(request):
    """Create/Issue a new certificate"""
    if request.method == 'POST':
        student_id = request.POST.get('student')
        course_id = request.POST.get('course')
        certificate_type = request.POST.get('certificate_type', 'completion')
        title = request.POST.get('title', 'Certificate of Completion')
        description = request.POST.get('description', '')
        completion_date = request.POST.get('completion_date')
        final_score = request.POST.get('final_score') or None
        grade = request.POST.get('grade', '')
        signed_by = request.POST.get('signed_by', '')
        signed_by_title = request.POST.get('signed_by_title', '')

        # Validate
        if not student_id or not course_id:
            messages.error(request, 'Student and Course are required.')
            return redirect('custom_admin:certificate_create')

        student = get_object_or_404(User, id=student_id)
        course = get_object_or_404(Course, id=course_id)

        # Check if an active (non-revoked) certificate already exists
        existing_certificate = Certificate.objects.filter(
            student=student,
            course=course,
            is_revoked=False
        ).first()

        if existing_certificate:
            messages.error(
                request,
                f'An active certificate ({existing_certificate.certificate_number}) already exists for {student.name} in {course.title}. '
                f'Please revoke the existing certificate before issuing a new one.'
            )
            return redirect('custom_admin:certificate_detail', certificate_id=existing_certificate.id)

        # Get enrollment if exists
        enrollment = Enrollment.objects.filter(
            course=course,
            user=student
        ).first()

        try:
            certificate = Certificate.objects.create(
                student=student,
                course=course,
                enrollment=enrollment,
                certificate_type=certificate_type,
                title=title,
                description=description,
                completion_date=completion_date or timezone.now().date(),
                final_score=final_score,
                grade=grade,
                signed_by=signed_by,
                signed_by_title=signed_by_title,
            )

            # Generate and save PDF
            try:
                from apps.courses.certificate_generator import generate_certificate_pdf
                from django.core.files.base import ContentFile

                pdf_buffer = generate_certificate_pdf(certificate)
                pdf_filename = f"certificate_{certificate.certificate_number}.pdf"
                certificate.pdf_file.save(pdf_filename, ContentFile(pdf_buffer.getvalue()), save=True)
            except Exception as pdf_error:
                # Log but don't fail - certificate is created, PDF can be regenerated
                import logging
                logging.getLogger(__name__).warning(f"Failed to generate PDF for certificate {certificate.id}: {pdf_error}")

            messages.success(request, f'Certificate {certificate.certificate_number} issued successfully!')
            return redirect('custom_admin:certificate_detail', certificate_id=certificate.id)
        except Exception as e:
            messages.error(request, f'Error creating certificate: {str(e)}')

    # Get data for form
    students = User.objects.filter(is_active=True, role='student').order_by('name')
    courses = Course.objects.filter(is_published=True).order_by('title')

    context = {
        'students': students,
        'courses': courses,
        'certificate_types': Certificate.CERTIFICATE_TYPES,
    }

    return render(request, 'custom_admin/certificates/form.html', context)


@user_passes_test(is_staff_user)
def certificate_detail_view(request, certificate_id):
    """View certificate details"""
    certificate = get_object_or_404(
        Certificate.objects.select_related('student', 'course', 'enrollment'),
        id=certificate_id
    )

    context = {
        'certificate': certificate,
    }

    return render(request, 'custom_admin/certificates/detail.html', context)


@user_passes_test(is_staff_user)
def certificate_download_view(request, certificate_id):
    """Download certificate as PDF"""
    from django.http import HttpResponse
    from apps.courses.certificate_generator import generate_certificate_pdf

    certificate = get_object_or_404(
        Certificate.objects.select_related('course', 'student'),
        id=certificate_id
    )

    # Generate PDF
    pdf_buffer = generate_certificate_pdf(certificate)

    # Create response
    response = HttpResponse(pdf_buffer.getvalue(), content_type='application/pdf')

    # Generate filename
    student_name = certificate.student.name or certificate.student.email
    safe_name = "".join(c for c in student_name if c.isalnum() or c in (' ', '-', '_')).strip()
    safe_course = "".join(c for c in certificate.course.title if c.isalnum() or c in (' ', '-', '_')).strip()
    filename = f"Certificate_{safe_name}_{safe_course}.pdf"

    response['Content-Disposition'] = f'attachment; filename="{filename}"'

    return response


@user_passes_test(is_staff_user)
def certificate_revoke_view(request, certificate_id):
    """Revoke a certificate"""
    certificate = get_object_or_404(Certificate, id=certificate_id)

    if request.method == 'POST':
        reason = request.POST.get('reason', '')
        certificate.revoke(reason=reason)
        messages.success(request, f'Certificate {certificate.certificate_number} has been revoked.')
        return redirect('custom_admin:certificate_detail', certificate_id=certificate.id)

    return redirect('custom_admin:certificate_detail', certificate_id=certificate.id)


@user_passes_test(is_staff_user)
def certificate_delete_view(request, certificate_id):
    """Delete a certificate"""
    certificate = get_object_or_404(Certificate, id=certificate_id)

    if request.method == 'POST':
        cert_number = certificate.certificate_number
        certificate.delete()
        messages.success(request, f'Certificate {cert_number} deleted successfully.')
        return redirect('custom_admin:certificates_list')

    return redirect('custom_admin:certificates_list')


def certificate_verify_view(request, verification_code):
    """Public verification page for certificates"""
    certificate = get_object_or_404(Certificate, verification_code=verification_code)

    context = {
        'certificate': certificate,
        'is_valid': certificate.is_valid,
    }

    return render(request, 'custom_admin/certificates/verify.html', context)


# =============================================================================
# STUDENT QUICK SEARCH & PROFILE
# =============================================================================

@user_passes_test(is_staff_user)
def student_search_api(request):
    """API endpoint for student quick search with autocomplete"""
    query = request.GET.get('q', '').strip()

    # Base queryset - only students
    students = User.objects.filter(role='student')

    if query:
        students = students.filter(
            Q(name__icontains=query) |
            Q(email__icontains=query) |
            Q(phone_number__icontains=query)
        )

    # Annotate with enrollment count and get analytics
    students = students.annotate(
        enrollments_count=Count('enrollments')
    ).select_related('analytics')[:10]

    results = []
    for student in students:
        # Get risk level from analytics if exists
        risk_level = None
        if hasattr(student, 'analytics') and student.analytics:
            risk_level = student.analytics.risk_level

        results.append({
            'id': student.id,
            'name': student.name or student.email,
            'email': student.email,
            'phone': student.phone_number or '',
            'enrollments_count': student.enrollments_count,
            'risk_level': risk_level,
        })

    return JsonResponse({'students': results})


@user_passes_test(is_staff_user)
def student_profile_view(request, student_id):
    """Comprehensive student profile page with all related data"""
    from apps.courses.models import StudentProgress

    # Get the student
    student = get_object_or_404(User, id=student_id, role='student')

    # Get enrollments with related data
    enrollments = Enrollment.objects.filter(user=student).select_related(
        'team', 'installment_plan_details'
    ).prefetch_related('payments', 'tax_invoices').order_by('-enrolled_on')

    # Calculate enrollment summaries
    enrollment_data = []
    total_paid = 0
    total_outstanding = 0

    for enrollment in enrollments:
        paid = enrollment.payments.filter(status='completed').aggregate(
            total=Sum('amount')
        )['total'] or 0
        outstanding = enrollment.outstanding_amount

        total_paid += paid
        total_outstanding += outstanding

        # Get course progress for this enrollment
        progress_percent = 0
        video_progress = StudentProgress.objects.filter(
            user=student, course=enrollment.course
        )
        if video_progress.exists():
            total_videos = video_progress.count()
            completed_count = video_progress.filter(completed=True).count()
            progress_percent = int((completed_count / total_videos) * 100) if total_videos > 0 else 0

        enrollment_data.append({
            'enrollment': enrollment,
            'paid': paid,
            'outstanding': outstanding,
            'progress': progress_percent,
        })

    # Get all payments for this student
    all_payments = Payment.objects.filter(
        enrollment__user=student
    ).select_related('enrollment').order_by('-created_at')

    # Get pending payments
    pending_payments = all_payments.filter(status__in=['pending', 'overdue'])

    # Get module progress
    module_progress = ModuleProgress.objects.filter(
        student=student
    ).select_related('module').order_by('-updated_at')

    # Get video progress
    video_progress = StudentProgress.objects.filter(
        user=student
    ).select_related('video_lesson').order_by('-last_watched_at')

    # Get analytics
    analytics = None
    try:
        analytics = StudentAnalytics.objects.get(student=student)
    except StudentAnalytics.DoesNotExist:
        pass

    # Get alerts
    alerts = ProgressAlert.objects.filter(student=student).order_by('-created_at')
    active_alerts = alerts.filter(is_resolved=False)
    resolved_alerts = alerts.filter(is_resolved=True)

    # Get mentor sessions
    mentor_sessions = MentorSession.objects.filter(
        student=student
    ).select_related('mentor').order_by('-session_date')

    # Get certificates
    certificates = Certificate.objects.filter(
        student=student
    ).order_by('-issue_date')

    # Get tax invoices
    tax_invoices = TaxInvoice.objects.filter(
        enrollment__user=student
    ).select_related('enrollment').order_by('-created_at')

    # Calculate quiz and assignment stats
    quiz_attempts = QuizAttempt.objects.filter(student=student)
    quiz_count = quiz_attempts.count()
    quiz_avg_score = quiz_attempts.aggregate(avg=Sum('score'))['avg'] or 0
    if quiz_count > 0:
        quiz_avg_score = quiz_avg_score / quiz_count

    assignment_submissions = AssignmentSubmission.objects.filter(student=student)
    assignment_count = assignment_submissions.count()

    context = {
        'student': student,
        'enrollment_data': enrollment_data,
        'total_enrollments': enrollments.count(),
        'total_paid': total_paid,
        'total_outstanding': total_outstanding,
        'all_payments': all_payments[:20],  # Last 20 payments
        'pending_payments': pending_payments,
        'module_progress': module_progress[:20],
        'video_progress': video_progress[:20],
        'analytics': analytics,
        'active_alerts': active_alerts,
        'resolved_alerts': resolved_alerts[:10],
        'mentor_sessions': mentor_sessions,
        'certificates': certificates,
        'tax_invoices': tax_invoices,
        'quiz_count': quiz_count,
        'quiz_avg_score': quiz_avg_score,
        'assignment_count': assignment_count,
    }

    return render(request, 'custom_admin/students/profile.html', context)
