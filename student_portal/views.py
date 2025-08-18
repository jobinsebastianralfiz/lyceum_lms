from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_protect, ensure_csrf_cookie
from django.middleware.csrf import get_token
from django.db.models import Q, Count, Avg
from django.core.paginator import Paginator
from django.utils import timezone
from apps.users.models import User
from apps.courses.models import (
    Course, Module, VideoLesson, StudentProgress, ModuleProgress,
    Assignment, Quiz, QuizQuestion, QuizChoice, AssignmentSubmission,
    QuizAttempt, QuizAnswer
)
from apps.payments.models import Enrollment, Payment, TaxInvoice, InstallmentPlan


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
            # Authenticate user
            user = authenticate(request, username=email, password=password)
            if user and hasattr(user, 'role') and user.role == 'student':
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


def student_logout(request):
    """Student logout"""
    logout(request)
    messages.success(request, 'You have been logged out successfully.')
    return redirect('student_portal:login')


def dashboard(request):
    """Student dashboard"""
    # Check authentication and role
    if not request.user.is_authenticated:
        messages.error(request, 'Please login to access the student portal.')
        return redirect('student_portal:login')
    
    if not hasattr(request.user, 'role') or request.user.role != 'student':
        messages.error(request, 'Access denied. Student role required.')
        return redirect('student_portal:login')
    
    user = request.user
    
    # Get student's enrollments
    enrollments = Enrollment.objects.filter(
        user=user, 
        active=True
    ).select_related('course', 'course__category').order_by('-enrolled_on')
    
    # Calculate statistics and add progress to each enrollment
    total_courses = enrollments.count()
    completed_courses = 0
    in_progress_courses = 0
    
    for enrollment in enrollments:
        # Calculate course progress using the same logic as course detail page
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
        
        # Count truly completed modules for statistics
        completed_modules = ModuleProgress.objects.filter(
            student=user,
            module__course=enrollment.course,
            is_completed=True
        ).count()
        
        # Attach progress to enrollment object for template access
        enrollment.progress_percentage = round(progress_percentage, 1)
        enrollment.completed_modules = completed_modules
        enrollment.total_modules = total_modules
        
        # Update overall statistics
        if total_modules > 0 and completed_modules == total_modules:
            completed_courses += 1
        elif completed_modules > 0:
            in_progress_courses += 1
    
    # Recent activity
    recent_progress = StudentProgress.objects.filter(
        user=user
    ).select_related('video_lesson', 'course').order_by('-last_watched_at')[:5]
    
    context = {
        'user': user,
        'enrollments': enrollments[:6],  # Show first 6 courses
        'total_courses': total_courses,
        'completed_courses': completed_courses,
        'in_progress_courses': in_progress_courses,
        'recent_activity': recent_progress,
    }
    
    return render(request, 'student_portal/dashboard.html', context)


def my_courses(request):
    """List all student's enrolled courses"""
    if not request.user.is_authenticated:
        return redirect('student_portal:login')
    
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
    
    # Apply status filter
    if status == 'completed':
        # Filter completed courses (this would need more complex logic)
        pass
    elif status == 'in_progress':
        # Filter in-progress courses
        pass
    
    # Pagination
    paginator = Paginator(enrollments, 12)
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
        return redirect('student_portal:login')
    
    user = request.user
    course = get_object_or_404(Course, id=course_id, is_published=True)
    
    # Check if user is enrolled
    try:
        enrollment = Enrollment.objects.get(user=user, course=course, active=True)
    except Enrollment.DoesNotExist:
        messages.error(request, 'You are not enrolled in this course.')
        return redirect('student_portal:my_courses')
    
    # Get modules with progress, assignments, and quizzes
    modules = course.modules.prefetch_related(
        'video_lessons', 'assignments', 'quizzes'
    ).order_by('order')
    
    # Get user's module progress and attach to each module
    for module in modules:
        try:
            progress = ModuleProgress.objects.get(student=user, module=module)
        except ModuleProgress.DoesNotExist:
            # Create initial progress if doesn't exist
            progress = ModuleProgress.objects.create(
                student=user,
                module=module,
                is_unlocked=(module.order == 1)  # Unlock first module
            )
        # Attach progress to module object for easy template access
        module.progress = progress
    
    context = {
        'course': course,
        'enrollment': enrollment,
        'modules': modules,
    }
    
    return render(request, 'student_portal/courses/course_detail.html', context)


def lesson_viewer(request, lesson_id):
    """Video lesson viewer"""
    if not request.user.is_authenticated:
        return redirect('student_portal:login')
    
    user = request.user
    lesson = get_object_or_404(VideoLesson, id=lesson_id)
    
    # Check if user is enrolled in the course
    try:
        enrollment = Enrollment.objects.get(
            user=user, 
            course=lesson.module.course, 
            active=True
        )
    except Enrollment.DoesNotExist:
        messages.error(request, 'You are not enrolled in this course.')
        return redirect('student_portal:my_courses')
    
    # Check if module is unlocked
    try:
        module_progress = ModuleProgress.objects.get(
            student=user, 
            module=lesson.module
        )
        if not module_progress.is_unlocked:
            messages.error(request, 'This module is not yet available.')
            return redirect('student_portal:course_detail', course_id=lesson.module.course.id)
    except ModuleProgress.DoesNotExist:
        messages.error(request, 'Module progress not found.')
        return redirect('student_portal:course_detail', course_id=lesson.module.course.id)
    
    # Get or create lesson progress
    progress, _ = StudentProgress.objects.get_or_create(
        user=user,
        course=lesson.module.course,
        video_lesson=lesson,
        defaults={'completed_percentage': 0.0}
    )
    
    # Get next and previous lessons
    current_module = lesson.module
    next_lesson = VideoLesson.objects.filter(
        module=current_module,
        order__gt=lesson.order
    ).order_by('order').first()
    
    prev_lesson = VideoLesson.objects.filter(
        module=current_module,
        order__lt=lesson.order
    ).order_by('-order').first()
    
    context = {
        'lesson': lesson,
        'progress': progress,
        'next_lesson': next_lesson,
        'prev_lesson': prev_lesson,
        'course': lesson.module.course,
        'module': current_module,
        'module_progress': module_progress,
    }
    
    return render(request, 'student_portal/courses/lesson_viewer.html', context)



def profile(request):
    """Student profile page"""
    if not request.user.is_authenticated:
        return redirect('student_portal:login')
    
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
    
    # Check enrollment
    try:
        Enrollment.objects.get(
            user=user, 
            course=lesson.module.course, 
            active=True
        )
    except Enrollment.DoesNotExist:
        return JsonResponse({'error': 'Not enrolled'}, status=403)
    
    # Get progress data
    completed_percentage = float(request.POST.get('completed_percentage', 0))
    completed = request.POST.get('completed', 'false').lower() == 'true'
    
    # Update progress
    progress, created = StudentProgress.objects.get_or_create(
        user=user,
        course=lesson.module.course,
        video_lesson=lesson,
        defaults={
            'completed_percentage': completed_percentage,
            'completed': completed
        }
    )
    
    if not created:
        progress.completed_percentage = max(progress.completed_percentage, completed_percentage)
        progress.completed = completed or progress.completed
        progress.save()
    
    # Update module progress
    module_progress = ModuleProgress.objects.get(student=user, module=lesson.module)
    module_progress.check_completion()
    
    return JsonResponse({
        'success': True,
        'completed_percentage': progress.completed_percentage,
        'completed': progress.completed
    })


def assignment_detail(request, assignment_id):
    """Assignment detail and submission interface"""
    if not request.user.is_authenticated:
        return redirect('student_portal:login')
    
    user = request.user
    assignment = get_object_or_404(Assignment, id=assignment_id)
    
    # Check if user is enrolled in the course
    try:
        enrollment = Enrollment.objects.get(
            user=user, 
            course=assignment.module.course, 
            active=True
        )
    except Enrollment.DoesNotExist:
        messages.error(request, 'You are not enrolled in this course.')
        return redirect('student_portal:my_courses')
    
    # Check if module is unlocked
    try:
        module_progress = ModuleProgress.objects.get(
            student=user, 
            module=assignment.module
        )
        if not module_progress.is_unlocked:
            messages.error(request, 'This module is not yet available.')
            return redirect('student_portal:course_detail', course_id=assignment.module.course.id)
    except ModuleProgress.DoesNotExist:
        messages.error(request, 'Module progress not found.')
        return redirect('student_portal:course_detail', course_id=assignment.module.course.id)
    
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
        'module': assignment.module,
        'course': assignment.module.course,
    }
    
    return render(request, 'student_portal/assignments/assignment_detail.html', context)


@require_http_methods(["POST"])
def submit_assignment(request, assignment_id):
    """Submit an assignment"""
    if not request.user.is_authenticated:
        return JsonResponse({'error': 'Authentication required'}, status=401)
    
    user = request.user
    assignment = get_object_or_404(Assignment, id=assignment_id)
    
    # Check enrollment
    try:
        Enrollment.objects.get(
            user=user, 
            course=assignment.module.course, 
            active=True
        )
    except Enrollment.DoesNotExist:
        return JsonResponse({'error': 'Not enrolled'}, status=403)
    
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
    
    return JsonResponse({
        'success': True,
        'submission_id': submission.id,
        'status': submission.status,
        'submitted_at': submission.submitted_at.isoformat() if submission.submitted_at else None
    })


def quiz_detail(request, quiz_id):
    """Quiz detail and taking interface"""
    if not request.user.is_authenticated:
        return redirect('student_portal:login')
    
    user = request.user
    quiz = get_object_or_404(Quiz, id=quiz_id)
    
    # Check if user is enrolled in the course
    try:
        enrollment = Enrollment.objects.get(
            user=user, 
            course=quiz.module.course, 
            active=True
        )
    except Enrollment.DoesNotExist:
        messages.error(request, 'You are not enrolled in this course.')
        return redirect('student_portal:my_courses')
    
    # Check if module is unlocked
    try:
        module_progress = ModuleProgress.objects.get(
            student=user, 
            module=quiz.module
        )
        if not module_progress.is_unlocked:
            messages.error(request, 'This module is not yet available.')
            return redirect('student_portal:course_detail', course_id=quiz.module.course.id)
    except ModuleProgress.DoesNotExist:
        messages.error(request, 'Module progress not found.')
        return redirect('student_portal:course_detail', course_id=quiz.module.course.id)
    
    # Get user's attempts (completed only)
    attempts = QuizAttempt.objects.filter(
        quiz=quiz,
        student=user,
        completed=True
    ).order_by('-completed_at')
    
    # Check if user can take another attempt
    attempt_count = attempts.count()
    can_attempt = attempt_count < quiz.max_attempts
    
    # Debug logging for attempt count issues
    print(f"DEBUG: Quiz {quiz.id} - User {user.id} - Attempts: {attempt_count}/{quiz.max_attempts} - Can attempt: {can_attempt}")
    
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
        'current_attempt': current_attempt,
        'enrollment': enrollment,
        'module': quiz.module,
        'course': quiz.module.course,
    }
    
    return render(request, 'student_portal/quizzes/quiz_detail.html', context)


@require_http_methods(["POST"])
def start_quiz_attempt(request, quiz_id):
    """Start a new quiz attempt"""
    if not request.user.is_authenticated:
        return JsonResponse({'error': 'Authentication required'}, status=401)
    
    user = request.user
    quiz = get_object_or_404(Quiz, id=quiz_id)
    
    # Check enrollment
    try:
        Enrollment.objects.get(
            user=user, 
            course=quiz.module.course, 
            active=True
        )
    except Enrollment.DoesNotExist:
        return JsonResponse({'error': 'Not enrolled'}, status=403)
    
    # Check attempt limit
    user_attempts = QuizAttempt.objects.filter(
        quiz=quiz,
        student=user,
        completed=True
    ).count()
    
    if user_attempts >= quiz.max_attempts:
        return JsonResponse({'error': 'Maximum attempts reached'}, status=400)
    
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
        return redirect('student_portal:login')
    
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
        return redirect('student_portal:login')
    
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
        return redirect('student_portal:login')
    
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
        return redirect('student_portal:login')
    
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
