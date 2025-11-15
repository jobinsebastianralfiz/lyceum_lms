from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_protect, ensure_csrf_cookie
from django.views.decorators.cache import never_cache, cache_control
from django.middleware.csrf import get_token
from django.db.models import Q, Count, Avg
from django.core.paginator import Paginator
from django.utils import timezone
from django.conf import settings
from datetime import date, timedelta
import razorpay
import json
from apps.users.models import User
from apps.courses.models import (
    Course, Module, VideoLesson, StudentProgress, ModuleProgress,
    Assignment, Quiz, QuizQuestion, QuizChoice, AssignmentSubmission,
    QuizAttempt, QuizAnswer, StudentAnalytics
)
from apps.payments.models import Enrollment, Payment, TaxInvoice, InstallmentPlan
from apps.ratings.models import CourseRating
from apps.content_management.models import News, Testimonial, Placement


@ensure_csrf_cookie
def student_login(request):
    """Student login page"""
    # Force CSRF cookie to be set
    get_token(request)
    
    # Check if already logged in
    if request.user.is_authenticated and hasattr(request.user, 'role') and request.user.role == 'student':
        return redirect('student_portal:dashboard')
    
    if request.method == 'POST':
        email = request.POST.get('email')
        password = request.POST.get('password')
        
        if email and password:
            # Try to authenticate with email as username
            user = authenticate(request, username=email, password=password)
            
            # If that fails, try to find user by email and authenticate with username
            if not user:
                try:
                    user_obj = User.objects.get(email=email)
                    user = authenticate(request, username=user_obj.username, password=password)
                except User.DoesNotExist:
                    pass
            
            # Check if user is valid and has student role (or no role restrictions for public users)
            if user and (hasattr(user, 'role') and user.role == 'student' or not user.is_staff):
                # Create session if it doesn't exist
                if not request.session.session_key:
                    request.session.create()
                
                # Log the user in
                login(request, user)
                
                # Force session save
                request.session.save()
                
                messages.success(request, f'Welcome back, {user.name}!')
                
                # Get redirect URL
                next_url = request.POST.get('next') or request.GET.get('next')
                if next_url and next_url != request.path:
                    return redirect(next_url)
                else:
                    return redirect('student_portal:dashboard')
            else:
                messages.error(request, 'Invalid credentials or account not found.')
        else:
            messages.error(request, 'Please provide both email and password.')
    
    # Ensure CSRF token is available
    context = {
        'csrf_token': get_token(request)
    }
    return render(request, 'student_portal/auth/login.html', context)


@login_required
def browse_courses(request):
    """Browse all available public courses"""
    if not request.user.is_authenticated:
        messages.error(request, 'Please login to access the student portal.')
        return redirect('landing:login')
    
    # Get all public courses
    courses = Course.objects.filter(
        is_published=True,
        allow_public_enrollment=True
    ).select_related('category').prefetch_related('ratings').order_by('-created_at')
    
    # Get user's enrollments for enrollment status
    user_enrollments = set(
        Enrollment.objects.filter(
            user=request.user,
            active=True
        ).values_list('course_id', flat=True)
    )
    
    # Add enrollment status to courses
    for course in courses:
        course.is_enrolled = course.id in user_enrollments
        course.user_rating = CourseRating.objects.filter(
            course=course,
            user=request.user
        ).first()
    
    # Search functionality
    search_query = request.GET.get('search', '')
    if search_query:
        courses = courses.filter(
            Q(title__icontains=search_query) |
            Q(description__icontains=search_query) |
            Q(category__name__icontains=search_query)
        )
    
    # Category filter
    category_filter = request.GET.get('category', '')
    if category_filter:
        courses = courses.filter(category__name=category_filter)
    
    # Pagination
    paginator = Paginator(courses, 9)  # 9 courses per page
    page_number = request.GET.get('page')
    courses_page = paginator.get_page(page_number)
    
    # Get categories for filter
    from apps.courses.models import Category
    categories = Category.objects.all().order_by('name')
    
    context = {
        'courses': courses_page,
        'categories': categories,
        'search_query': search_query,
        'category_filter': category_filter,
        'user_enrollments': user_enrollments,
    }
    return render(request, 'student_portal/browse_courses.html', context)


@cache_control(no_cache=True, must_revalidate=True, no_store=True)
def student_logout(request):
    """Student logout with cache clearing"""
    logout(request)
    messages.success(request, 'You have been logged out successfully.')
    response = redirect('landing:login')
    # Add headers to prevent caching
    response['Cache-Control'] = 'no-cache, no-store, must-revalidate, max-age=0'
    response['Pragma'] = 'no-cache'
    response['Expires'] = '0'
    return response


@never_cache
@cache_control(no_cache=True, must_revalidate=True, no_store=True)
def dashboard(request):
    """Enhanced modern student dashboard"""
    # Check authentication and role
    if not request.user.is_authenticated:
        messages.error(request, 'Please login to access the student portal.')
        return redirect('landing:login')

    if not hasattr(request.user, 'role') or request.user.role != 'student':
        messages.error(request, 'Access denied. Student role required.')
        return redirect('landing:login')
    
    user = request.user
    
    # Get student's enrollments with detailed progress
    enrollments = Enrollment.objects.filter(
        user=user, 
        active=True
    ).select_related('course', 'course__category').order_by('-enrolled_on')
    
    # Enhanced statistics calculation
    total_courses = enrollments.count()
    completed_courses = 0
    
    # Video completion stats
    completed_videos = StudentProgress.objects.filter(
        user=user,
        completed=True
    ).count()
    
    total_videos_in_enrolled_courses = 0
    
    for enrollment in enrollments:
        course = enrollment.course
        modules = course.modules.all()

        # Calculate video progress using many-to-many relationships
        course_videos = VideoLesson.objects.filter(
            module_links__module__course_links__course=course
        ).distinct().count()
        completed_videos_in_course = StudentProgress.objects.filter(
            user=user,
            course=course,
            completed=True
        ).count()
        
        total_videos_in_enrolled_courses += course_videos
        
        # Calculate course progress
        total_modules = modules.count()
        if total_modules > 0:
            total_progress = 0
            modules_with_progress = 0
            
            for module in modules:
                try:
                    module_progress = ModuleProgress.objects.get(student=user, module=module)
                    total_progress += module_progress.completion_percentage
                    modules_with_progress += 1
                except ModuleProgress.DoesNotExist:
                    modules_with_progress += 1
            
            progress_percentage = total_progress / modules_with_progress if modules_with_progress > 0 else 0
        else:
            progress_percentage = 0
        
        # Count completed modules using many-to-many relationships
        completed_modules = ModuleProgress.objects.filter(
            student=user,
            module__course_links__course=enrollment.course,
            is_completed=True
        ).count()
        
        # Attach data to enrollment
        enrollment.progress_percentage = round(progress_percentage, 1)
        enrollment.completed_modules = completed_modules
        enrollment.total_modules = total_modules
        enrollment.total_videos = course_videos
        enrollment.completed_videos = completed_videos_in_course
        
        if total_modules > 0 and completed_modules == total_modules:
            completed_courses += 1
    
    # Assignment statistics
    submitted_assignments = AssignmentSubmission.objects.filter(
        student=user
    ).exclude(status='draft').count()

    # Get total assignments for enrolled courses using many-to-many
    enrolled_course_ids = [e.course.id for e in enrollments]
    total_assignments = Assignment.objects.filter(
        module_links__module__course_links__course_id__in=enrolled_course_ids
    ).distinct().count()
    
    # Quiz statistics
    quiz_attempts = QuizAttempt.objects.filter(
        student=user,
        completed=True
    )
    quiz_attempts_count = quiz_attempts.count()
    # Calculate average quiz score manually since score_percentage is a property
    if quiz_attempts_count > 0:
        total_percentage = 0
        for attempt in quiz_attempts:
            total_percentage += attempt.score_percentage
        average_quiz_score = total_percentage / quiz_attempts_count
    else:
        average_quiz_score = 0
    
    # Modules completed
    modules_completed = ModuleProgress.objects.filter(
        student=user,
        is_completed=True
    ).count()
    
    # Weekly activity
    week_ago = timezone.now() - timedelta(days=7)
    videos_this_week = StudentProgress.objects.filter(
        user=user,
        last_watched_at__gte=week_ago,
        completed=True
    ).count()
    
    assignments_this_week = AssignmentSubmission.objects.filter(
        student=user,
        created_at__gte=week_ago
    ).exclude(status='draft').count()
    
    # Recent activity with more details
    # Note: Can't use select_related for video_lesson__module since it's now many-to-many
    recent_progress = StudentProgress.objects.filter(
        user=user
    ).select_related('video_lesson', 'course').order_by('-last_watched_at')[:15]

    # Continue Learning - Get last watched video that's not completed
    continue_learning = StudentProgress.objects.filter(
        user=user,
        completed=False,
        completed_percentage__gt=0
    ).select_related('video_lesson', 'course').order_by('-last_watched_at').first()

    # If no in-progress video, get the most recent completed one
    if not continue_learning:
        continue_learning = StudentProgress.objects.filter(
            user=user,
            completed=True
        ).select_related('video_lesson', 'course').order_by('-last_watched_at').first()

    # Calculate learning streak (consecutive days with activity)
    learning_streak = 0
    current_date = timezone.now().date()
    for i in range(365):  # Check up to 1 year
        check_date = current_date - timedelta(days=i)
        has_activity = StudentProgress.objects.filter(
            user=user,
            last_watched_at__date=check_date
        ).exists() or AssignmentSubmission.objects.filter(
            student=user,
            created_at__date=check_date
        ).exists()

        if has_activity:
            learning_streak = i + 1
        elif i > 0:  # If no activity and not today, break streak
            break

    # Calculate total learning time (estimate based on video progress)
    total_learning_minutes = 0
    for progress in StudentProgress.objects.filter(user=user, completed=True):
        if progress.video_lesson and progress.video_lesson.duration_seconds:
            total_learning_minutes += progress.video_lesson.duration_seconds / 60

    # Upcoming assignments (within next 7 days)
    upcoming_deadline = timezone.now() + timedelta(days=7)
    upcoming_assignments = []

    for enrollment in enrollments:
        for module in enrollment.course.modules.all():
            for module_assignment in module.assignment_links.all():
                assignment = module_assignment.assignment
                try:
                    # Check if student hasn't submitted this assignment
                    AssignmentSubmission.objects.get(student=user, assignment=assignment)
                except AssignmentSubmission.DoesNotExist:
                    # Calculate days until due (rough estimate based on module start)
                    days_until_due = 7  # Default
                    upcoming_assignments.append({
                        'title': assignment.title,
                        'course': enrollment.course.title,
                        'days_until_due': days_until_due,
                        'assignment': assignment
                    })
    
    context = {
        'user': user,
        'current_time': timezone.now(),

        # Continue Learning
        'continue_learning': continue_learning,
        'learning_streak': learning_streak,
        'total_learning_hours': round(total_learning_minutes / 60, 1),

        # Course data
        'enrollments': enrollments[:6],
        'all_enrollments': enrollments,  # For full course list
        'enrolled_courses_count': total_courses,
        'completed_courses': completed_courses,

        # Statistics
        'completed_videos_count': completed_videos,
        'submitted_assignments': submitted_assignments,
        'total_assignments': total_assignments,
        'quiz_attempts_count': quiz_attempts_count,
        'average_quiz_score': average_quiz_score,
        'modules_completed': modules_completed,

        # Weekly activity
        'videos_this_week': videos_this_week,
        'assignments_this_week': assignments_this_week,

        # Activity feeds
        'recent_progress': recent_progress,
        'upcoming_assignments': upcoming_assignments[:5],

        # Content Management - Latest content for student dashboard
        'latest_news': News.objects.filter(is_published=True, is_featured=True).order_by('-published_at')[:3],
        'featured_testimonials': Testimonial.objects.filter(is_published=True, is_featured=True).order_by('-created_at')[:3],
        'recent_placements': Placement.objects.filter(is_published=True, is_featured=True).order_by('-published_at')[:4],
    }
    
    # Use modern dashboard
    response = render(request, 'student_portal/dashboard_modern.html', context)
    # Add cache prevention headers
    response['Cache-Control'] = 'no-cache, no-store, must-revalidate, max-age=0'
    response['Pragma'] = 'no-cache'
    response['Expires'] = '0'
    return response



def my_courses(request):
    """List all student's enrolled courses"""
    if not request.user.is_authenticated:
        return redirect('landing:login')
    
    user = request.user
    
    # Get search and filter parameters
    search = request.GET.get('search', '')
    status = request.GET.get('status', 'all')  # all, in_progress, completed
    
    # Base queryset
    enrollments = Enrollment.objects.filter(
        user=user, 
        active=True
    ).select_related('course', 'course__category')
    
    # Apply search
    if search:
        enrollments = enrollments.filter(
            Q(course__title__icontains=search) |
            Q(course__description__icontains=search)
        )
    
    # Store enrollments list before pagination for filtering
    enrollments_list = list(enrollments)
    
    # Calculate progress for each enrollment (same logic as dashboard)
    for enrollment in enrollments_list:
        modules = enrollment.course.modules.all()
        total_modules = modules.count()
        
        if total_modules > 0:
            total_progress = 0
            modules_with_progress = 0
            
            for module in modules:
                try:
                    module_progress = ModuleProgress.objects.get(student=user, module=module)
                    total_progress += module_progress.completion_percentage
                    modules_with_progress += 1
                except ModuleProgress.DoesNotExist:
                    # Module not started, contributes 0% to progress
                    modules_with_progress += 1
            
            # Calculate average completion across all modules
            progress_percentage = total_progress / modules_with_progress if modules_with_progress > 0 else 0
        else:
            progress_percentage = 0
        
        # Count truly completed modules for statistics using many-to-many
        completed_modules = ModuleProgress.objects.filter(
            student=user,
            module__course_links__course=enrollment.course,
            is_completed=True
        ).count()
        
        # Attach progress to enrollment object for template access
        enrollment.progress_percentage = round(progress_percentage, 1)
        enrollment.completed_modules = completed_modules
        enrollment.total_modules = total_modules
    
    # Apply status filter after progress calculation
    if status == 'completed':
        enrollments_list = [e for e in enrollments_list if e.completed_modules == e.total_modules and e.total_modules > 0]
    elif status == 'in_progress':
        enrollments_list = [e for e in enrollments_list if e.completed_modules < e.total_modules and e.completed_modules > 0]
    
    # Pagination
    paginator = Paginator(enrollments_list, 12)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'page_obj': page_obj,
        'search': search,
        'status': status,
    }
    
    return render(request, 'student_portal/courses/my_courses.html', context)


def course_detail(request, course_id):
    """Course detail and learning interface"""
    if not request.user.is_authenticated:
        return redirect('landing:login')
    
    user = request.user
    course = get_object_or_404(Course, id=course_id, is_published=True)
    
    # Check if user is enrolled
    enrollment = None
    is_enrolled = False
    try:
        enrollment = Enrollment.objects.get(user=user, course=course, active=True)
        is_enrolled = True
    except Enrollment.DoesNotExist:
        is_enrolled = False
    
    # Get user's rating for this course
    user_rating = None
    if is_enrolled:
        user_rating = CourseRating.objects.filter(
            course=course,
            user=request.user
        ).first()
    
    if is_enrolled:
        # For enrolled users - show full course content
        # Get modules through the CourseModule through table to access the order field
        from apps.courses.models import CourseModule
        course_modules = CourseModule.objects.filter(
            course=course
        ).select_related('module').prefetch_related(
            'module__video_links__video_lesson',
            'module__assignment_links__assignment',
            'module__quiz_links__quiz'
        ).order_by('order')

        # Extract modules and attach order
        modules = []
        for cm in course_modules:
            module = cm.module
            module.course_order = cm.order  # Attach the order from CourseModule

            # Count content through the many-to-many relationships
            module.videos_count = module.video_links.count()
            module.assignments_count = module.assignment_links.count()
            module.quizzes_count = module.quiz_links.count()

            modules.append(module)

        # Get user's module progress and attach to each module
        for module in modules:
            try:
                progress = ModuleProgress.objects.get(student=user, module=module)
            except ModuleProgress.DoesNotExist:
                # Create initial progress if doesn't exist
                progress = ModuleProgress.objects.create(
                    student=user,
                    module=module,
                    is_unlocked=True  # Unlock all modules
                )
            # Attach progress to module object for easy template access
            module.progress = progress

        context = {
            'course': course,
            'enrollment': enrollment,
            'modules': modules,
            'is_enrolled': True,
            'user_rating': user_rating,
        }
        return render(request, 'student_portal/courses/course_detail.html', context)
    else:
        # For non-enrolled users - show course preview and purchase option
        # Get first 3 modules via CourseModule for proper ordering
        from apps.courses.models import CourseModule
        course_modules = CourseModule.objects.filter(
            course=course
        ).select_related('module').prefetch_related(
            'module__video_links__video_lesson',
            'module__assignment_links__assignment',
            'module__quiz_links__quiz'
        ).order_by('order')[:3]

        modules = []
        for cm in course_modules:
            module = cm.module
            module.course_order = cm.order

            # Count content through the many-to-many relationships
            module.videos_count = module.video_links.count()
            module.assignments_count = module.assignment_links.count()
            module.quizzes_count = module.quiz_links.count()

            modules.append(module)

        context = {
            'course': course,
            'modules': modules,
            'is_enrolled': False,
            'can_purchase': True,
            'user_rating': user_rating,
        }
    
    return render(request, 'student_portal/courses/course_detail.html', context)


def course_checkout(request, course_id):
    """Razorpay checkout page for course purchase"""
    if not request.user.is_authenticated:
        return redirect('landing:login')
    
    user = request.user
    course = get_object_or_404(Course, id=course_id, is_published=True)
    
    # Check if already enrolled
    existing_enrollment = Enrollment.objects.filter(user=user, course=course, active=True).first()
    if existing_enrollment:
        messages.info(request, 'You are already enrolled in this course.')
        return redirect('student_portal:course_detail', course_id=course.id)
    
    # Calculate pricing
    base_price = float(course.price)
    discount_amount = 0
    
    # Calculate tax (18% GST)
    tax_rate = 0.18
    tax_amount = base_price * tax_rate
    total_amount = base_price + tax_amount
    
    # Convert to paisa (Razorpay expects amount in paisa)
    razorpay_amount = int(total_amount * 100)
    
    # Check if Razorpay is configured
    razorpay_key_id = getattr(settings, 'RAZORPAY_KEY_ID', '')
    if not razorpay_key_id:
        messages.error(request, f'Payment gateway is not configured. Key: {razorpay_key_id}. Please contact support.')
        return redirect('student_portal:course_detail', course_id=course.id)
    
    context = {
        'course': course,
        'user': user,
        'base_price': base_price,
        'discount_amount': discount_amount,
        'tax_amount': tax_amount,
        'tax_rate': int(tax_rate * 100),
        'total_amount': total_amount,
        'razorpay_amount': razorpay_amount,
        'razorpay_key_id': razorpay_key_id,
    }
    
    return render(request, 'student_portal/courses/checkout.html', context)


@require_http_methods(["POST"])
def verify_payment(request):
    """Verify Razorpay payment and create enrollment"""
    if not request.user.is_authenticated:
        return JsonResponse({'error': 'Authentication required'}, status=401)
    
    try:
        # Get payment data from request
        data = json.loads(request.body)
        razorpay_payment_id = data.get('razorpay_payment_id')
        razorpay_order_id = data.get('razorpay_order_id') 
        razorpay_signature = data.get('razorpay_signature')
        course_id = data.get('course_id')
        
        if not all([razorpay_payment_id, razorpay_order_id, razorpay_signature, course_id]):
            return JsonResponse({'error': 'Missing required payment data'}, status=400)
        
        # Initialize Razorpay client
        client = razorpay.Client(
            auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET)
        )
        
        # Verify payment signature
        params_dict = {
            'razorpay_order_id': razorpay_order_id,
            'razorpay_payment_id': razorpay_payment_id,
            'razorpay_signature': razorpay_signature
        }
        
        try:
            client.utility.verify_payment_signature(params_dict)
        except:
            return JsonResponse({'error': 'Payment verification failed'}, status=400)
        
        # Get course and user
        course = get_object_or_404(Course, id=course_id, is_published=True)
        user = request.user
        
        # Check if already enrolled
        if Enrollment.objects.filter(user=user, course=course, active=True).exists():
            return JsonResponse({'error': 'Already enrolled in this course'}, status=400)
        
        # Calculate amounts (same logic as checkout)
        base_price = float(course.price)
        tax_amount = base_price * 0.18
        total_amount = base_price + tax_amount
        
        # Create enrollment and payment records
        enrollment = Enrollment.objects.create(
            user=user,
            course=course,
            total_amount=total_amount,
            tax_amount=tax_amount,
            payment_status='completed'
        )
        
        payment = Payment.objects.create(
            enrollment=enrollment,
            amount=total_amount,
            tax_amount=tax_amount,
            payment_method='razorpay',
            transaction_id=razorpay_payment_id,
            payment_date=timezone.now(),
            due_date=date.today(),
            status='completed',
            razorpay_order_id=razorpay_order_id,
            razorpay_payment_id=razorpay_payment_id,
            razorpay_signature=razorpay_signature
        )
        
        # Create Tax Invoice for paid courses
        if total_amount > 0:
            from apps.payments.models import TaxInvoice
            from datetime import datetime
            
            invoice_number = f"INV-{enrollment.id}-{payment.id}-{datetime.now().strftime('%Y%m%d')}"
            tax_invoice = TaxInvoice.objects.create(
                enrollment=enrollment,
                payment=payment,
                invoice_number=invoice_number,
                subtotal=total_amount - tax_amount,  # Base price without tax
                tax_rate=18.0,  # GST rate
                tax_amount=tax_amount,
                total_amount=total_amount
            )
            
            # Send enrollment confirmation email with invoice
            try:
                from emails.invoice_generator import generate_invoice_pdf
                from emails.utils import send_enrollment_confirmation_email
                
                # Generate PDF invoice
                invoice_pdf_content = generate_invoice_pdf(tax_invoice)
                
                # Send enrollment confirmation email with invoice attachment
                email_sent = send_enrollment_confirmation_email(
                    enrollment, 
                    include_invoice=True, 
                    invoice_pdf_content=invoice_pdf_content
                )
                
                if not email_sent:
                    print(f"Warning: Failed to send enrollment confirmation email to {user.email}")
                        
            except Exception as email_error:
                print(f"Error sending enrollment email: {str(email_error)}")
                # Continue without failing the payment process
        else:
            # For free courses, still send enrollment confirmation without invoice
            try:
                from emails.utils import send_enrollment_confirmation_email
                send_enrollment_confirmation_email(enrollment, include_invoice=False)
            except Exception as email_error:
                print(f"Error sending enrollment email: {str(email_error)}")
        
        return JsonResponse({
            'success': True,
            'message': 'Payment successful! Course enrollment completed.',
            'enrollment_id': enrollment.id,
            'redirect_url': f'/student-portal/course/{course.id}/'
        })
        
    except Exception as e:
        return JsonResponse({'error': f'Payment processing failed: {str(e)}'}, status=500)


def lesson_viewer(request, lesson_id):
    """Video lesson viewer"""
    if not request.user.is_authenticated:
        return redirect('landing:login')

    user = request.user
    lesson = get_object_or_404(VideoLesson, id=lesson_id)

    # Get the first module this lesson belongs to
    current_module = lesson.get_first_module()

    if not current_module:
        messages.error(request, 'This lesson is not assigned to any module.')
        return redirect('student_portal:dashboard')

    # Get all courses that have this module
    from apps.courses.models import CourseModule
    course_modules = CourseModule.objects.filter(
        module=current_module
    ).select_related('course')

    if not course_modules.exists():
        messages.error(request, 'This module is not assigned to any course.')
        return redirect('student_portal:dashboard')

    # Check if user is enrolled in ANY course that has this module
    enrollment = None
    course = None

    for cm in course_modules:
        try:
            enrollment = Enrollment.objects.get(
                user=user,
                course=cm.course,
                active=True
            )
            course = cm.course
            break  # Found an enrollment, use this course
        except Enrollment.DoesNotExist:
            continue

    if not enrollment or not course:
        messages.error(request, 'You are not enrolled in any course containing this lesson.')
        return redirect('student_portal:my_courses')

    # Get or create module progress and ensure it's unlocked
    module_progress, created = ModuleProgress.objects.get_or_create(
        student=user,
        module=current_module,
        defaults={
            'is_unlocked': True,
            'is_completed': False,
            'completion_percentage': 0.0
        }
    )

    # Check if module is unlocked
    if not module_progress.is_unlocked:
        messages.error(request, 'This module is not yet available.')
        return redirect('student_portal:course_detail', course_id=course.id)
    
    # Get or create lesson progress
    # Note: Database constraint is on (user, video_lesson) only, not course
    progress, created = StudentProgress.objects.get_or_create(
        user=user,
        video_lesson=lesson,
        defaults={
            'course': course,
            'completed_percentage': 0.0
        }
    )

    # Update course if it changed (due to many-to-many relationships)
    if not created and progress.course != course:
        progress.course = course
        progress.save()
    
    # Get next and previous lessons through ModuleVideo through table
    from apps.courses.models import ModuleVideo

    # Get current lesson's order in this module
    try:
        current_mv = ModuleVideo.objects.get(module=current_module, video_lesson=lesson)
        current_order = current_mv.order

        # Get next lesson
        next_mv = ModuleVideo.objects.filter(
            module=current_module,
            order__gt=current_order
        ).select_related('video_lesson').order_by('order').first()
        next_lesson = next_mv.video_lesson if next_mv else None

        # Get previous lesson
        prev_mv = ModuleVideo.objects.filter(
            module=current_module,
            order__lt=current_order
        ).select_related('video_lesson').order_by('-order').first()
        prev_lesson = prev_mv.video_lesson if prev_mv else None
    except ModuleVideo.DoesNotExist:
        next_lesson = None
        prev_lesson = None

    context = {
        'lesson': lesson,
        'progress': progress,
        'next_lesson': next_lesson,
        'prev_lesson': prev_lesson,
        'course': course,
        'module': current_module,
        'module_progress': module_progress,
    }

    return render(request, 'student_portal/courses/lesson_viewer.html', context)



def profile(request):
    """Student profile page"""
    if not request.user.is_authenticated:
        return redirect('landing:login')
    
    user = request.user
    
    if request.method == 'POST':
        # Update profile
        user.name = request.POST.get('name', user.name)
        user.phone_number = request.POST.get('phone_number', user.phone_number)
        user.address = request.POST.get('address', user.address)
        user.save()
        
        messages.success(request, 'Profile updated successfully!')
        return redirect('student_portal:profile')
    
    # Get enrollment statistics
    enrollments = Enrollment.objects.filter(user=user, active=True)
    total_courses = enrollments.count()
    
    context = {
        'user': user,
        'total_courses': total_courses,
    }
    
    return render(request, 'student_portal/profile.html', context)


@require_http_methods(["POST"])
def change_password(request):
    """Change user password"""
    if not request.user.is_authenticated:
        return JsonResponse({'error': 'Authentication required'}, status=401)
    
    user = request.user
    
    # Get form data
    current_password = request.POST.get('current_password')
    new_password = request.POST.get('new_password')
    confirm_password = request.POST.get('confirm_password')
    
    # Validate inputs
    if not all([current_password, new_password, confirm_password]):
        return JsonResponse({'error': 'All fields are required'}, status=400)
    
    if new_password != confirm_password:
        return JsonResponse({'error': 'New password and confirmation do not match'}, status=400)
    
    if len(new_password) < 8:
        return JsonResponse({'error': 'Password must be at least 8 characters long'}, status=400)
    
    # Check current password
    if not user.check_password(current_password):
        return JsonResponse({'error': 'Current password is incorrect'}, status=400)
    
    # Update password
    user.set_password(new_password)
    user.save()
    
    # Re-authenticate user to maintain session
    from django.contrib.auth import update_session_auth_hash
    update_session_auth_hash(request, user)
    
    return JsonResponse({'success': True, 'message': 'Password changed successfully'})


@require_http_methods(["POST"])
def update_lesson_progress(request, lesson_id):
    """AJAX endpoint to update lesson progress"""
    if not request.user.is_authenticated:
        return JsonResponse({'error': 'Authentication required'}, status=401)

    user = request.user
    lesson = get_object_or_404(VideoLesson, id=lesson_id)

    # Get the first module this lesson belongs to
    current_module = lesson.get_first_module()

    if not current_module:
        return JsonResponse({'error': 'Lesson not assigned to any module'}, status=400)

    # Get all courses that have this module and check enrollment
    from apps.courses.models import CourseModule
    course_modules = CourseModule.objects.filter(
        module=current_module
    ).select_related('course')

    enrollment = None
    course = None

    for cm in course_modules:
        try:
            enrollment = Enrollment.objects.get(
                user=user,
                course=cm.course,
                active=True
            )
            course = cm.course
            break
        except Enrollment.DoesNotExist:
            continue

    if not enrollment or not course:
        return JsonResponse({'error': 'Not enrolled in any course with this lesson'}, status=403)

    # Get progress data
    completed_percentage = float(request.POST.get('completed_percentage', 0))
    completed = request.POST.get('completed', 'false').lower() == 'true'

    # Update progress
    progress, created = StudentProgress.objects.get_or_create(
        user=user,
        video_lesson=lesson,
        defaults={
            'course': course,
            'completed_percentage': completed_percentage,
            'completed': completed
        }
    )

    if not created:
        progress.completed_percentage = max(progress.completed_percentage, completed_percentage)
        progress.completed = completed or progress.completed
        # Update course if it changed (due to many-to-many relationships)
        if progress.course != course:
            progress.course = course
        progress.save()

    # Get or create module progress
    module_progress, mp_created = ModuleProgress.objects.get_or_create(
        student=user,
        module=current_module,
        defaults={
            'is_unlocked': True,
            'is_completed': False,
            'completion_percentage': 0.0
        }
    )
    module_progress.check_completion()
    
    # Update analytics for mentoring system
    from apps.courses.models import StudentAnalytics
    analytics, created = StudentAnalytics.objects.get_or_create(student=user)
    analytics.last_login = timezone.now()
    analytics.total_videos_watched = StudentProgress.objects.filter(user=user, completed=True).count()
    analytics.save()
    
    return JsonResponse({
        'success': True,
        'completed_percentage': progress.completed_percentage,
        'completed': progress.completed
    })


def assignment_detail(request, assignment_id):
    """Assignment detail and submission interface"""
    if not request.user.is_authenticated:
        return redirect('landing:login')

    user = request.user
    assignment = get_object_or_404(Assignment, id=assignment_id)

    # Get the first module this assignment belongs to
    current_module = assignment.get_first_module()

    if not current_module:
        messages.error(request, 'This assignment is not assigned to any module.')
        return redirect('student_portal:dashboard')

    # Get all courses that have this module and check enrollment
    from apps.courses.models import CourseModule
    course_modules = CourseModule.objects.filter(
        module=current_module
    ).select_related('course')

    enrollment = None
    course = None

    for cm in course_modules:
        try:
            enrollment = Enrollment.objects.get(
                user=user,
                course=cm.course,
                active=True
            )
            course = cm.course
            break
        except Enrollment.DoesNotExist:
            continue

    if not enrollment or not course:
        messages.error(request, 'You are not enrolled in any course containing this assignment.')
        return redirect('student_portal:my_courses')

    # Get or create module progress and ensure it's unlocked
    module_progress, created = ModuleProgress.objects.get_or_create(
        student=user,
        module=current_module,
        defaults={
            'is_unlocked': True,
            'is_completed': False,
            'completion_percentage': 0.0
        }
    )

    # Check if module is unlocked
    if not module_progress.is_unlocked:
        messages.error(request, 'This module is not yet available.')
        return redirect('student_portal:course_detail', course_id=course.id)

    # Get existing submission if any
    submission = None
    try:
        submission = AssignmentSubmission.objects.get(
            assignment=assignment,
            student=user
        )
    except AssignmentSubmission.DoesNotExist:
        pass

    context = {
        'assignment': assignment,
        'submission': submission,
        'enrollment': enrollment,
        'module': current_module,
        'course': course,
    }

    return render(request, 'student_portal/assignments/assignment_detail.html', context)


@require_http_methods(["POST"])
def submit_assignment(request, assignment_id):
    """Submit an assignment"""
    if not request.user.is_authenticated:
        return JsonResponse({'error': 'Authentication required'}, status=401)

    user = request.user
    assignment = get_object_or_404(Assignment, id=assignment_id)

    # Get the first module this assignment belongs to
    current_module = assignment.get_first_module()

    if not current_module:
        return JsonResponse({'error': 'Assignment not assigned to any module'}, status=400)

    # Get all courses that have this module and check enrollment
    from apps.courses.models import CourseModule
    course_modules = CourseModule.objects.filter(
        module=current_module
    ).select_related('course')

    enrollment = None

    for cm in course_modules:
        try:
            enrollment = Enrollment.objects.get(
                user=user,
                course=cm.course,
                active=True
            )
            break
        except Enrollment.DoesNotExist:
            continue

    if not enrollment:
        return JsonResponse({'error': 'Not enrolled in any course with this assignment'}, status=403)
    
    # Get form data
    github_url = request.POST.get('github_url', '').strip()
    submission_notes = request.POST.get('submission_notes', '').strip()
    
    if not github_url:
        return JsonResponse({'error': 'GitHub URL is required'}, status=400)
    
    # Check if submission already exists
    try:
        submission = AssignmentSubmission.objects.get(
            assignment=assignment,
            student=user
        )
        if submission.status != 'draft':
            return JsonResponse({'error': 'Assignment already submitted'}, status=400)
        
        # Update existing draft
        submission.github_url = github_url
        submission.submission_notes = submission_notes
        submission.save()
        
    except AssignmentSubmission.DoesNotExist:
        # Create new submission
        submission = AssignmentSubmission.objects.create(
            assignment=assignment,
            student=user,
            github_url=github_url,
            submission_notes=submission_notes
        )
    
    # Submit the assignment
    submission.submit()
    
    # Update module progress
    module_progress = ModuleProgress.objects.get(student=user, module=assignment.module)
    module_progress.check_completion()
    
    # Update student analytics in real-time
    try:
        analytics, _ = StudentAnalytics.objects.get_or_create(student=user)
        
        # Update assignment metrics
        analytics.total_assignments_submitted = AssignmentSubmission.objects.filter(
            student=user
        ).exclude(status='draft').count()
        
        # Update modules completed
        analytics.modules_completed = user.module_progress.filter(
            is_completed=True
        ).count()
        
        # Update last activity
        analytics.last_activity_date = timezone.now()
        
        # Recalculate risk score
        analytics.calculate_risk_score()
        analytics.save()
        
    except Exception as e:
        # Log error but don't break assignment submission
        print(f"Error updating analytics for user {user.id}: {e}")
    
    return JsonResponse({
        'success': True,
        'submission_id': submission.id,
        'status': submission.status,
        'submitted_at': submission.submitted_at.isoformat() if submission.submitted_at else None
    })


def quiz_detail(request, quiz_id):
    """Quiz detail and taking interface"""
    if not request.user.is_authenticated:
        return redirect('landing:login')

    user = request.user
    quiz = get_object_or_404(Quiz, id=quiz_id)

    # Get the first module this quiz belongs to
    current_module = quiz.get_first_module()

    if not current_module:
        messages.error(request, 'This quiz is not assigned to any module.')
        return redirect('student_portal:dashboard')

    # Get all courses that have this module and check enrollment
    from apps.courses.models import CourseModule
    course_modules = CourseModule.objects.filter(
        module=current_module
    ).select_related('course')

    enrollment = None
    course = None

    for cm in course_modules:
        try:
            enrollment = Enrollment.objects.get(
                user=user,
                course=cm.course,
                active=True
            )
            course = cm.course
            break
        except Enrollment.DoesNotExist:
            continue

    if not enrollment or not course:
        messages.error(request, 'You are not enrolled in any course containing this quiz.')
        return redirect('student_portal:my_courses')

    # Get or create module progress and ensure it's unlocked
    module_progress, created = ModuleProgress.objects.get_or_create(
        student=user,
        module=current_module,
        defaults={
            'is_unlocked': True,
            'is_completed': False,
            'completion_percentage': 0.0
        }
    )

    # Check if module is unlocked
    if not module_progress.is_unlocked:
        messages.error(request, 'This module is not yet available.')
        return redirect('student_portal:course_detail', course_id=course.id)
    
    # Get user's attempts (completed only)
    attempts = QuizAttempt.objects.filter(
        quiz=quiz,
        student=user,
        completed=True
    ).order_by('-completed_at')
    
    # Allow unlimited attempts - removed max_attempts restriction
    attempt_count = attempts.count()
    can_attempt = True  # Always allow attempts
    unlimited_attempts = True  # Flag for template to show "Unlimited"

    # Debug logging for attempt count issues
    print(f"DEBUG: Quiz {quiz.id} - User {user.id} - Attempts: {attempt_count} - Can attempt: {can_attempt} (unlimited)")

    # Get current attempt (if any)
    current_attempt = QuizAttempt.objects.filter(
        quiz=quiz,
        student=user,
        completed=False
    ).first()

    # Get quiz questions for display
    questions = quiz.questions.prefetch_related('choices').order_by('order')

    context = {
        'quiz': quiz,
        'questions': questions,
        'attempts': attempts,
        'can_attempt': can_attempt,
        'unlimited_attempts': unlimited_attempts,
        'current_attempt': current_attempt,
        'enrollment': enrollment,
        'module': current_module,
        'course': course,
    }
    
    return render(request, 'student_portal/quizzes/quiz_detail.html', context)


@require_http_methods(["POST"])
def start_quiz_attempt(request, quiz_id):
    """Start a new quiz attempt"""
    if not request.user.is_authenticated:
        return JsonResponse({'error': 'Authentication required'}, status=401)

    user = request.user
    quiz = get_object_or_404(Quiz, id=quiz_id)

    # Get the first module this quiz belongs to
    current_module = quiz.get_first_module()

    if not current_module:
        return JsonResponse({'error': 'Quiz not assigned to any module'}, status=400)

    # Get all courses that have this module and check enrollment
    from apps.courses.models import CourseModule
    course_modules = CourseModule.objects.filter(
        module=current_module
    ).select_related('course')

    enrollment = None

    for cm in course_modules:
        try:
            enrollment = Enrollment.objects.get(
                user=user,
                course=cm.course,
                active=True
            )
            break
        except Enrollment.DoesNotExist:
            continue

    if not enrollment:
        return JsonResponse({'error': 'Not enrolled in any course with this quiz'}, status=403)
    
    # Removed max_attempts restriction - allow unlimited attempts
    user_attempts = QuizAttempt.objects.filter(
        quiz=quiz,
        student=user,
        completed=True
    ).count()
    
    # No longer checking attempt limit - unlimited attempts allowed
    
    # Check if there's already an active attempt
    existing_attempt = QuizAttempt.objects.filter(
        quiz=quiz,
        student=user,
        completed=False
    ).first()
    
    if existing_attempt:
        return JsonResponse({
            'success': True,
            'attempt_id': existing_attempt.id,
            'started_at': existing_attempt.started_at.isoformat()
        })
    
    # Create new attempt
    attempt = QuizAttempt.objects.create(
        quiz=quiz,
        student=user,
        attempt_number=user_attempts + 1,
        total_points=quiz.total_points
    )
    
    return JsonResponse({
        'success': True,
        'attempt_id': attempt.id,
        'started_at': attempt.started_at.isoformat()
    })


@require_http_methods(["POST"])
def submit_quiz_answers(request, attempt_id):
    """Submit quiz answers"""
    if not request.user.is_authenticated:
        return JsonResponse({'error': 'Authentication required'}, status=401)
    
    user = request.user
    
    try:
        attempt = QuizAttempt.objects.get(
            id=attempt_id,
            student=user,
            completed=False
        )
    except QuizAttempt.DoesNotExist:
        return JsonResponse({'error': 'Quiz attempt not found or already completed'}, status=404)
    
    # Get answers from form data
    answers_data = []
    for key, value in request.POST.items():
        if key.startswith('question_'):
            question_id = key.replace('question_', '')
            try:
                question_id = int(question_id)
                choice_id = int(value) if value else None
                answers_data.append({
                    'question': question_id,
                    'selected_choice': choice_id
                })
            except (ValueError, TypeError):
                continue
    
    total_score = 0
    
    for answer_data in answers_data:
        question_id = answer_data.get('question')
        selected_choice_id = answer_data.get('selected_choice')
        
        try:
            question = QuizQuestion.objects.get(id=question_id, quiz=attempt.quiz)
        except QuizQuestion.DoesNotExist:
            continue
        
        points_earned = 0
        is_correct = False
        
        if selected_choice_id and question.question_type in ['multiple_choice', 'true_false']:
            try:
                selected_choice = QuizChoice.objects.get(id=selected_choice_id)
                is_correct = selected_choice.is_correct
                if is_correct:
                    points_earned = question.points
            except QuizChoice.DoesNotExist:
                pass
        
        # Create quiz answer
        QuizAnswer.objects.create(
            attempt=attempt,
            question=question,
            selected_choice_id=selected_choice_id,
            is_correct=is_correct,
            points_earned=points_earned
        )
        
        total_score += points_earned
    
    # Update attempt
    attempt.score = total_score
    
    # Calculate time taken (in seconds)
    if attempt.started_at:
        time_taken_seconds = int((timezone.now() - attempt.started_at).total_seconds())
        attempt.time_taken = time_taken_seconds
    
    attempt.complete()
    
    # Update module progress
    try:
        module_progress = ModuleProgress.objects.get(
            student=user,
            module=attempt.quiz.module
        )
        module_progress.check_completion()
    except ModuleProgress.DoesNotExist:
        pass
    
    # Update student analytics in real-time
    try:
        from django.db.models import Avg
        analytics, _ = StudentAnalytics.objects.get_or_create(student=user)
        
        # Update quiz metrics
        analytics.total_quizzes_attempted = QuizAttempt.objects.filter(
            student=user, completed=True
        ).count()
        
        # Update average quiz score
        # Calculate percentage in database using actual fields
        from django.db.models import F, FloatField
        from django.db.models.functions import Cast

        quiz_attempts = QuizAttempt.objects.filter(
            student=user,
            completed=True
        ).exclude(total_points=0)

        if quiz_attempts.exists():
            quiz_avg = quiz_attempts.aggregate(
                avg_score=Avg(
                    Cast(F('score'), FloatField()) * 100.0 / Cast(F('total_points'), FloatField())
                )
            )['avg_score']
            analytics.avg_quiz_score = quiz_avg or 0
        else:
            analytics.avg_quiz_score = 0
        
        # Update modules completed
        analytics.modules_completed = user.module_progress.filter(
            is_completed=True
        ).count()
        
        # Update last activity
        analytics.last_activity_date = timezone.now()
        
        # Recalculate risk score
        analytics.calculate_risk_score()
        analytics.save()
        
    except Exception as e:
        # Log error but don't break quiz submission
        print(f"Error updating analytics for user {user.id}: {e}")
    
    return JsonResponse({
        'success': True,
        'score': total_score,
        'total_points': attempt.total_points,
        'percentage': attempt.score_percentage,
        'passed': attempt.is_passed,
        'completed_at': attempt.completed_at.isoformat()
    })


def my_payments(request):
    """List all student's payments and payment status"""
    if not request.user.is_authenticated:
        return redirect('landing:login')
    
    user = request.user
    
    # Get user's enrollments with payment information
    enrollments = Enrollment.objects.filter(
        user=user, 
        active=True
    ).select_related('course').order_by('-enrolled_on')
    
    # Add payment details to each enrollment
    for enrollment in enrollments:
        # Get all payments for this enrollment
        enrollment.all_payments = Payment.objects.filter(
            enrollment=enrollment
        ).order_by('installment_number')
        
        # Get installment plan if exists
        enrollment.installment_plan_obj = enrollment.installment_plan
    
    context = {
        'enrollments': enrollments,
    }
    
    return render(request, 'student_portal/payments/my_payments.html', context)


def payment_detail(request, enrollment_id):
    """Detailed payment view for a specific enrollment"""
    if not request.user.is_authenticated:
        return redirect('landing:login')
    
    user = request.user
    enrollment = get_object_or_404(
        Enrollment, 
        id=enrollment_id, 
        user=user, 
        active=True
    )
    
    # Get all payments for this enrollment
    payments = Payment.objects.filter(
        enrollment=enrollment
    ).order_by('installment_number')
    
    # Get installment plan if exists
    installment_plan = enrollment.installment_plan
    
    context = {
        'enrollment': enrollment,
        'payments': payments,
        'installment_plan': installment_plan,
    }
    
    return render(request, 'student_portal/payments/payment_detail.html', context)


def my_invoices(request):
    """List all student's tax invoices"""
    if not request.user.is_authenticated:
        return redirect('landing:login')
    
    user = request.user
    
    # Get all tax invoices for user's enrollments
    invoices = TaxInvoice.objects.filter(
        enrollment__user=user,
        enrollment__active=True
    ).select_related('enrollment', 'enrollment__course', 'payment').order_by('-invoice_date')
    
    context = {
        'invoices': invoices,
    }
    
    return render(request, 'student_portal/payments/my_invoices.html', context)


def invoice_detail(request, invoice_id):
    """Detailed view of a specific tax invoice"""
    if not request.user.is_authenticated:
        return redirect('landing:login')
    
    user = request.user
    invoice = get_object_or_404(
        TaxInvoice,
        id=invoice_id,
        enrollment__user=user,
        enrollment__active=True
    )
    
    context = {
        'invoice': invoice,
    }
    
    return render(request, 'student_portal/payments/invoice_detail.html', context)



def live_sessions(request):
    """Show student's live sessions - upcoming, live now, and past"""
    if not request.user.is_authenticated:
        return redirect('landing:login')
    
    from apps.live_sessions.models import LiveSession, SessionParticipant
    from django.db.models import Prefetch
    
    user = request.user
    
    # Get sessions where user is a participant
    participant_sessions = SessionParticipant.objects.filter(
        student=user
    ).values_list('session_id', flat=True)
    
    # Get live sessions (currently happening)
    live_sessions = LiveSession.objects.filter(
        id__in=participant_sessions,
        status='live'
    ).select_related('course', 'created_by').order_by('scheduled_date')
    
    # Get upcoming sessions
    upcoming_sessions = LiveSession.objects.filter(
        id__in=participant_sessions,
        status='scheduled',
        scheduled_date__gt=timezone.now()
    ).select_related('course', 'created_by').order_by('scheduled_date')
    
    # Get past sessions
    past_sessions = LiveSession.objects.filter(
        id__in=participant_sessions,
        status='ended'
    ).select_related('course', 'created_by').order_by('-scheduled_date')[:20]
    
    context = {
        'live_sessions': live_sessions,
        'upcoming_sessions': upcoming_sessions,
        'past_sessions': past_sessions,
    }
    
    return render(request, 'student_portal/live_sessions.html', context)




def settings(request):
    """Student settings page"""
    if not request.user.is_authenticated:
        return redirect('landing:login')
    
    return render(request, 'student_portal/settings.html')


def help_support(request):
    """Help and support page with FAQs"""
    if not request.user.is_authenticated:
        return redirect('landing:login')
    
    return render(request, 'student_portal/help_support.html')

