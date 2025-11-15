from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse, HttpResponse
from django.views.decorators.http import require_http_methods
from django.db.models import Q, Avg, Sum
from django.core.paginator import Paginator
from django.utils import timezone
from datetime import timedelta

from apps.users.models import User
from apps.courses.models import (
    Course, StudentAnalytics, ProgressAlert, MentorSession,
    StudentProgress, QuizAttempt, AssignmentSubmission
)


@login_required
def mentor_dashboard(request):
    """Main mentor dashboard with overview of all students"""
    if not hasattr(request.user, 'role') or request.user.role not in ['admin', 'instructor']:
        messages.error(request, 'Access denied. Mentor role required.')
        return redirect('custom_admin:login')
    
    # Ensure all students have analytics records
    from apps.users.models import User
    students = User.objects.filter(role='student', is_active=True)
    
    # Create analytics records for students who don't have them
    for student in students:
        analytics, created = StudentAnalytics.objects.get_or_create(student=student)
        if created:
            # Update new analytics record with current data
            analytics.update_metrics()
    
    # Get all students with analytics (now guaranteed to exist)
    students_with_analytics = StudentAnalytics.objects.select_related('student').all()
    
    # Risk level distribution
    risk_distribution = {
        'critical': students_with_analytics.filter(risk_level='critical').count(),
        'high': students_with_analytics.filter(risk_level='high').count(),
        'medium': students_with_analytics.filter(risk_level='medium').count(),
        'low': students_with_analytics.filter(risk_level='low').count(),
    }
    
    # Get pagination parameters
    critical_page = request.GET.get('critical_page', 1)
    alerts_page = request.GET.get('alerts_page', 1)
    
    # Students needing immediate attention with pagination
    critical_students_qs = students_with_analytics.filter(
        risk_level__in=['critical', 'high']
    ).order_by('-risk_score')
    
    from django.core.paginator import Paginator
    critical_paginator = Paginator(critical_students_qs, 4)  # 4 per page
    critical_students = critical_paginator.get_page(critical_page)
    
    # Recent alerts with pagination
    recent_alerts_qs = ProgressAlert.objects.filter(
        is_resolved=False
    ).select_related('student', 'course').order_by('-created_at')
    
    alerts_paginator = Paginator(recent_alerts_qs, 4)  # 4 per page
    recent_alerts = alerts_paginator.get_page(alerts_page)
    
    # Engagement stats
    total_students = students_with_analytics.count()
    active_students = students_with_analytics.filter(
        last_login__gte=timezone.now() - timedelta(days=7)
    ).count()
    
    # Calculate percentages for progress bars
    critical_percentage = round((risk_distribution['critical'] / total_students * 100), 1) if total_students > 0 else 0
    high_percentage = round((risk_distribution['high'] / total_students * 100), 1) if total_students > 0 else 0
    
    # Get recent mentoring sessions with pagination
    sessions_page = request.GET.get('sessions_page', 1)
    recent_sessions_qs = MentorSession.objects.filter(
        mentor=request.user
    ).select_related('student', 'course').order_by('-session_date')
    
    sessions_paginator = Paginator(recent_sessions_qs, 5)  # 5 per page
    recent_sessions = sessions_paginator.get_page(sessions_page)
    
    # Session statistics for current mentor
    total_sessions = recent_sessions_qs.count()
    sessions_this_week = recent_sessions_qs.filter(
        session_date__gte=timezone.now() - timedelta(days=7)
    ).count()
    
    context = {
        'risk_distribution': risk_distribution,
        'critical_students': critical_students,
        'recent_alerts': recent_alerts,
        'total_students': total_students,
        'active_students': active_students,
        'inactive_percentage': round((total_students - active_students) / total_students * 100, 1) if total_students > 0 else 0,
        'critical_percentage': critical_percentage,
        'high_percentage': high_percentage,
        # Session data
        'recent_sessions': recent_sessions,
        'total_sessions': total_sessions,
        'sessions_this_week': sessions_this_week,
    }
    
    return render(request, 'custom_admin/mentor/dashboard.html', context)


@login_required
def student_analytics_list(request):
    """List all students with filtering and search"""
    if not hasattr(request.user, 'role') or request.user.role not in ['admin', 'instructor']:
        messages.error(request, 'Access denied. Mentor role required.')
        return redirect('custom_admin:login')
    
    # Get filter parameters
    risk_level = request.GET.get('risk_level', 'all')
    course_id = request.GET.get('course', 'all')
    search = request.GET.get('search', '')
    sort_by = request.GET.get('sort', 'risk_score')  # risk_score, last_login, name
    
    # Base queryset
    students = StudentAnalytics.objects.select_related('student').all()
    
    # Apply filters
    if risk_level != 'all':
        students = students.filter(risk_level=risk_level)
    
    if course_id != 'all':
        # Filter by students enrolled in specific course
        enrolled_student_ids = User.objects.filter(
            enrollments__course_id=course_id,
            enrollments__active=True
        ).values_list('id', flat=True)
        students = students.filter(student_id__in=enrolled_student_ids)
    
    if search:
        students = students.filter(
            Q(student__name__icontains=search) |
            Q(student__email__icontains=search)
        )
    
    # Apply sorting
    if sort_by == 'risk_score':
        students = students.order_by('-risk_score')
    elif sort_by == 'last_login':
        students = students.order_by('-last_login')
    elif sort_by == 'name':
        students = students.order_by('student__name')
    
    # Pagination
    paginator = Paginator(students, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    # Get courses for filter dropdown
    courses = Course.objects.filter(is_published=True).order_by('title')
    
    context = {
        'page_obj': page_obj,
        'courses': courses,
        'risk_level': risk_level,
        'course_id': course_id,
        'search': search,
        'sort_by': sort_by,
    }
    
    return render(request, 'custom_admin/mentor/student_list.html', context)


@login_required
def student_detail(request, student_id):
    """Detailed view of individual student analytics"""
    if not hasattr(request.user, 'role') or request.user.role not in ['admin', 'instructor']:
        messages.error(request, 'Access denied. Mentor role required.')
        return redirect('custom_admin:login')
    
    student = get_object_or_404(User, id=student_id, role='student')
    analytics, _ = StudentAnalytics.objects.get_or_create(student=student)
    
    # Get student's enrollments and progress
    enrollments = student.enrollments.filter(active=True).select_related('course')
    
    # Calculate detailed progress for each course
    course_progress = []
    for enrollment in enrollments:
        course = enrollment.course

        # Get modules through CourseModule many-to-many
        from apps.courses.models import CourseModule, ModuleVideo, ModuleQuiz, ModuleAssignment
        course_modules = CourseModule.objects.filter(course=course).select_related('module')
        module_ids = [cm.module.id for cm in course_modules]

        # Video progress - get videos through ModuleVideo many-to-many
        module_videos = ModuleVideo.objects.filter(module_id__in=module_ids)
        video_lesson_ids = [mv.video_lesson_id for mv in module_videos]

        videos_total = len(video_lesson_ids)
        videos_completed = StudentProgress.objects.filter(
            user=student,
            video_lesson_id__in=video_lesson_ids,
            completed=True
        ).count()

        # Quiz progress - get quizzes through ModuleQuiz many-to-many
        module_quizzes = ModuleQuiz.objects.filter(module_id__in=module_ids)
        quiz_ids = [mq.quiz_id for mq in module_quizzes]

        quiz_attempts = QuizAttempt.objects.filter(
            student=student,
            quiz_id__in=quiz_ids,
            completed=True
        )

        # Assignment progress - get assignments through ModuleAssignment many-to-many
        module_assignments = ModuleAssignment.objects.filter(module_id__in=module_ids)
        assignment_ids = [ma.assignment_id for ma in module_assignments]

        assignment_submissions = AssignmentSubmission.objects.filter(
            student=student,
            assignment_id__in=assignment_ids
        ).exclude(status='draft')
        
        course_progress.append({
            'course': course,
            'videos_total': videos_total,
            'videos_completed': videos_completed,
            'video_completion_rate': (videos_completed / videos_total * 100) if videos_total > 0 else 0,
            'quiz_attempts': quiz_attempts.count(),
            'avg_quiz_score': quiz_attempts.aggregate(avg=Avg('score'))['avg'] or 0,
            'assignments_submitted': assignment_submissions.count(),
        })
    
    # Recent activity
    recent_progress = StudentProgress.objects.filter(
        user=student
    ).select_related('video_lesson', 'course').order_by('-last_watched_at')[:10]
    
    # Get alerts for this student
    alerts = ProgressAlert.objects.filter(
        student=student
    ).select_related('course').order_by('-created_at')[:10]
    
    # Get mentoring sessions
    sessions = MentorSession.objects.filter(
        student=student
    ).select_related('mentor', 'course').order_by('-session_date')[:10]
    
    context = {
        'student': student,
        'analytics': analytics,
        'course_progress': course_progress,
        'recent_progress': recent_progress,
        'alerts': alerts,
        'sessions': sessions,
    }
    
    return render(request, 'custom_admin/mentor/student_detail.html', context)


@login_required
def alerts_list(request):
    """List and manage progress alerts"""
    if not hasattr(request.user, 'role') or request.user.role not in ['admin', 'instructor']:
        messages.error(request, 'Access denied. Mentor role required.')
        return redirect('custom_admin:login')
    
    # Filter parameters
    alert_type = request.GET.get('type', 'all')
    priority = request.GET.get('priority', 'all')
    status = request.GET.get('status', 'active')  # active, resolved, all
    
    # Base queryset
    alerts = ProgressAlert.objects.select_related('student', 'course', 'resolved_by')
    
    # Apply filters
    if alert_type != 'all':
        alerts = alerts.filter(alert_type=alert_type)
    
    if priority != 'all':
        alerts = alerts.filter(priority=priority)
    
    if status == 'active':
        alerts = alerts.filter(is_resolved=False)
    elif status == 'resolved':
        alerts = alerts.filter(is_resolved=True)
    
    alerts = alerts.order_by('-created_at')
    
    # Pagination
    paginator = Paginator(alerts, 25)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'page_obj': page_obj,
        'alert_type': alert_type,
        'priority': priority,
        'status': status,
        'alert_types': ProgressAlert.ALERT_TYPES,
        'alert_priorities': ProgressAlert.ALERT_PRIORITY,
    }
    
    return render(request, 'custom_admin/mentor/alerts_list.html', context)


@require_http_methods(["POST"])
def resolve_alert(request, alert_id):
    """Resolve an alert"""
    if not hasattr(request.user, 'role') or request.user.role not in ['admin', 'instructor']:
        return JsonResponse({'error': 'Access denied'}, status=403)
    
    alert = get_object_or_404(ProgressAlert, id=alert_id)
    notes = request.POST.get('notes', '')
    
    alert.resolve(resolved_by=request.user, notes=notes)
    
    return JsonResponse({
        'success': True,
        'message': 'Alert resolved successfully'
    })


@login_required
def create_mentor_session(request):
    """Create a new mentoring session"""
    if not hasattr(request.user, 'role') or request.user.role not in ['admin', 'instructor']:
        messages.error(request, 'Access denied. Mentor role required.')
        return redirect('custom_admin:login')
    
    # Get context data first (needed for form re-rendering on error)
    students = User.objects.filter(role='student', is_active=True).order_by('name')
    courses = Course.objects.filter(is_published=True).order_by('title')
    
    context = {
        'students': students,
        'courses': courses,
        'session_types': MentorSession.SESSION_TYPES,
    }
    
    if request.method == 'POST':
        # Process form submission
        student_id = request.POST.get('student_id')
        course_id = request.POST.get('course_id')
        session_type = request.POST.get('session_type')
        duration_minutes = request.POST.get('duration_minutes')
        topics_discussed = request.POST.get('topics_discussed')
        action_items = request.POST.get('action_items', '')
        follow_up_required = request.POST.get('follow_up_required') == 'on'
        follow_up_date = request.POST.get('follow_up_date') or None
        mentor_notes = request.POST.get('mentor_notes', '')
        session_date = request.POST.get('session_date')
        
        try:
            # Validate required fields
            if not student_id:
                messages.error(request, 'Student selection is required.')
                return render(request, 'custom_admin/mentor/create_session.html', context)
            
            if not session_type:
                messages.error(request, 'Session type is required.')
                return render(request, 'custom_admin/mentor/create_session.html', context)
            
            if not duration_minutes or int(duration_minutes) <= 0:
                messages.error(request, 'Valid duration is required.')
                return render(request, 'custom_admin/mentor/create_session.html', context)
            
            if not topics_discussed.strip():
                messages.error(request, 'Topics discussed is required.')
                return render(request, 'custom_admin/mentor/create_session.html', context)
            
            student = User.objects.get(id=student_id, role='student')
            course = Course.objects.get(id=course_id) if course_id else None
            
            # Create the session
            session = MentorSession.objects.create(
                mentor=request.user,
                student=student,
                course=course,
                session_type=session_type,
                duration_minutes=int(duration_minutes),
                topics_discussed=topics_discussed,
                action_items=action_items,
                follow_up_required=follow_up_required,
                follow_up_date=follow_up_date,
                mentor_notes=mentor_notes,
                session_date=session_date
            )
            
            # Update student analytics
            analytics, created = StudentAnalytics.objects.get_or_create(student=student)
            analytics.last_mentor_contact = timezone.now()
            analytics.save()
            
            messages.success(request, f'Mentoring session recorded successfully! Session ID: {session.id}')
            return redirect('mentor:student_detail', student_id=student.id)
            
        except User.DoesNotExist:
            messages.error(request, 'Selected student not found.')
        except Course.DoesNotExist:
            messages.error(request, 'Selected course not found.')
        except ValueError as e:
            messages.error(request, f'Invalid input: {str(e)}')
        except Exception as e:
            messages.error(request, f'Error creating session: {str(e)}')
            # Log the full error for debugging
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f'Error creating mentor session: {e}', exc_info=True)
    
    return render(request, 'custom_admin/mentor/create_session.html', context)


@login_required
def mentor_sessions_list(request):
    """List all mentor sessions by the current mentor"""
    if not hasattr(request.user, 'role') or request.user.role not in ['admin', 'instructor']:
        messages.error(request, 'Access denied. Mentor role required.')
        return redirect('custom_admin:login')
    
    # Filter parameters
    student_id = request.GET.get('student', 'all')
    course_id = request.GET.get('course', 'all')
    session_type = request.GET.get('session_type', 'all')
    search = request.GET.get('search', '')
    
    # Base queryset - sessions by current mentor
    sessions = MentorSession.objects.filter(
        mentor=request.user
    ).select_related('student', 'course')
    
    # Apply filters
    if student_id != 'all':
        sessions = sessions.filter(student_id=student_id)
    
    if course_id != 'all':
        sessions = sessions.filter(course_id=course_id)
    
    if session_type != 'all':
        sessions = sessions.filter(session_type=session_type)
    
    if search:
        sessions = sessions.filter(
            Q(student__name__icontains=search) |
            Q(student__email__icontains=search) |
            Q(topics_discussed__icontains=search) |
            Q(action_items__icontains=search)
        )
    
    sessions = sessions.order_by('-session_date')
    
    # Pagination
    paginator = Paginator(sessions, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    # Get filter options
    students = User.objects.filter(
        role='student', 
        mentoring_sessions__mentor=request.user
    ).distinct().order_by('name')
    
    courses = Course.objects.filter(
        is_published=True,
        mentoring_sessions__mentor=request.user
    ).distinct().order_by('title')
    
    # Session statistics
    total_sessions = sessions.count()
    total_duration = sessions.aggregate(
        total=Sum('duration_minutes')
    )['total'] or 0
    avg_duration = sessions.aggregate(
        avg=Avg('duration_minutes')
    )['avg'] or 0
    
    context = {
        'page_obj': page_obj,
        'students': students,
        'courses': courses,
        'session_types': MentorSession.SESSION_TYPES,
        'student_id': student_id,
        'course_id': course_id,
        'session_type': session_type,
        'search': search,
        'total_sessions': total_sessions,
        'total_duration': total_duration,
        'avg_duration': round(avg_duration, 1),
    }
    
    return render(request, 'custom_admin/mentor/sessions_list.html', context)


@login_required
def mentor_test(request):
    """Temporary test view to debug mentor functionality"""
    return HttpResponse(f"Mentor test working! User: {request.user.username}, Role: {getattr(request.user, 'role', 'No role')}")