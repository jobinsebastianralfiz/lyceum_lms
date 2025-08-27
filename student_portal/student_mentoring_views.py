from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Count, Avg, Sum
from django.core.paginator import Paginator
from django.utils import timezone
from datetime import timedelta

from apps.courses.models import (
    MentorSession, StudentAnalytics, StudentProgress, 
    QuizAttempt, AssignmentSubmission, Course
)


@login_required
def student_mentoring_dashboard(request):
    """Student's mentoring dashboard - shows their mentoring progress and insights"""
    # Check if user is a student
    if not hasattr(request.user, 'role') or request.user.role != 'student':
        messages.error(request, 'Access denied. Student role required.')
        return redirect('student_portal:login')
    
    student = request.user
    
    # Get or create analytics (safe access)
    analytics, created = StudentAnalytics.objects.get_or_create(student=student)
    
    # Get mentoring sessions (student-appropriate fields only)
    recent_sessions = MentorSession.objects.filter(
        student=student
    ).select_related('mentor', 'course').order_by('-session_date')[:5]
    
    total_sessions = MentorSession.objects.filter(student=student).count()
    
    # Calculate study insights
    study_insights = {
        'total_videos_watched': analytics.total_videos_watched,
        'total_assignments_submitted': analytics.total_assignments_submitted,
        'total_quizzes_attempted': analytics.total_quizzes_attempted,
        'avg_quiz_score': analytics.avg_quiz_score,
        'modules_completed': analytics.modules_completed,
    }
    
    # Get recent activity
    recent_activity = StudentProgress.objects.filter(
        user=student
    ).select_related('video_lesson', 'course').order_by('-last_watched_at')[:10]
    
    # Calculate weekly progress
    week_ago = timezone.now() - timedelta(days=7)
    videos_watched = StudentProgress.objects.filter(
        user=student, 
        last_watched_at__gte=week_ago,
        completed=True
    ).count()
    
    weekly_progress = {
        'videos_watched': videos_watched,
        'quiz_attempts': QuizAttempt.objects.filter(
            student=student,
            completed_at__gte=week_ago
        ).count(),
        'assignments_submitted': AssignmentSubmission.objects.filter(
            student=student,
            created_at__gte=week_ago
        ).exclude(status='draft').count(),
        'videos_progress_stroke': min(videos_watched * 31.4 / 10, 251.2),  # For SVG circle
    }
    
    # Get improvement suggestions based on performance
    suggestions = []
    if analytics.avg_quiz_score < 70:
        suggestions.append({
            'type': 'quiz_performance',
            'title': 'Quiz Performance',
            'message': 'Consider reviewing course materials before taking quizzes. Your current average is {}%.'.format(analytics.avg_quiz_score),
            'icon': 'fas fa-clipboard-list',
            'color': 'warning'
        })
    
    if analytics.total_videos_watched < 5:
        suggestions.append({
            'type': 'video_completion',
            'title': 'Video Learning',
            'message': 'Watching more video lessons can help improve your understanding of the concepts.',
            'icon': 'fas fa-video',
            'color': 'info'
        })
    
    if weekly_progress['videos_watched'] == 0:
        suggestions.append({
            'type': 'weekly_activity',
            'title': 'Weekly Activity',
            'message': 'Try to maintain consistent study habits by watching at least a few videos each week.',
            'icon': 'fas fa-calendar-week',
            'color': 'primary'
        })
    
    # Positive reinforcement
    achievements = []
    if analytics.modules_completed > 0:
        achievements.append({
            'title': 'Module Completion',
            'message': f'Great job! You\'ve completed {analytics.modules_completed} modules.',
            'icon': 'fas fa-trophy',
            'color': 'success'
        })
    
    if analytics.avg_quiz_score >= 80:
        achievements.append({
            'title': 'Quiz Excellence',
            'message': f'Excellent work! Your quiz average is {analytics.avg_quiz_score:.0f}%.',
            'icon': 'fas fa-star',
            'color': 'success'
        })
    
    context = {
        'student': student,
        'analytics': analytics,
        'recent_sessions': recent_sessions,
        'total_sessions': total_sessions,
        'study_insights': study_insights,
        'recent_activity': recent_activity,
        'weekly_progress': weekly_progress,
        'suggestions': suggestions,
        'achievements': achievements,
    }
    
    return render(request, 'student_portal/mentoring/dashboard.html', context)


@login_required
def student_session_history(request):
    """Student's complete mentoring session history"""
    if not hasattr(request.user, 'role') or request.user.role != 'student':
        messages.error(request, 'Access denied. Student role required.')
        return redirect('student_portal:login')
    
    student = request.user
    
    # Get all sessions with pagination
    sessions_list = MentorSession.objects.filter(
        student=student
    ).select_related('mentor', 'course').order_by('-session_date')
    
    paginator = Paginator(sessions_list, 10)  # 10 sessions per page
    page_number = request.GET.get('page')
    sessions = paginator.get_page(page_number)
    
    # Get session statistics
    session_stats = {
        'total_sessions': sessions_list.count(),
        'total_duration': sessions_list.aggregate(
            total=Sum('duration_minutes')
        )['total'] or 0,
        'avg_duration': sessions_list.aggregate(
            avg=Avg('duration_minutes')
        )['avg'] or 0,
        'sessions_this_month': sessions_list.filter(
            session_date__gte=timezone.now().replace(day=1)
        ).count(),
    }
    
    context = {
        'sessions': sessions,
        'session_stats': session_stats,
    }
    
    return render(request, 'student_portal/mentoring/session_history.html', context)


@login_required
def student_progress_insights(request):
    """Detailed progress insights for students"""
    if not hasattr(request.user, 'role') or request.user.role != 'student':
        messages.error(request, 'Access denied. Student role required.')
        return redirect('student_portal:login')
    
    student = request.user
    analytics, created = StudentAnalytics.objects.get_or_create(student=student)
    
    # Get course-wise progress
    enrollments = student.enrollments.filter(active=True).select_related('course')
    course_insights = []
    
    for enrollment in enrollments:
        course = enrollment.course
        modules = course.modules.all()
        
        # Calculate detailed progress
        total_videos = sum(module.video_lessons.count() for module in modules)
        completed_videos = StudentProgress.objects.filter(
            user=student,
            video_lesson__module__course=course,
            completed=True
        ).count()
        
        quiz_attempts = QuizAttempt.objects.filter(
            student=student,
            quiz__module__course=course,
            completed=True
        )
        
        assignment_submissions = AssignmentSubmission.objects.filter(
            student=student,
            assignment__module__course=course
        ).exclude(status='draft')
        
        completion_percentage = (completed_videos / total_videos * 100) if total_videos > 0 else 0
        course_insights.append({
            'course': course,
            'total_videos': total_videos,
            'completed_videos': completed_videos,
            'completion_percentage': completion_percentage,
            'completion_degrees': completion_percentage * 3.6,  # For conic gradient
            'quiz_attempts': quiz_attempts.count(),
            'avg_quiz_score': quiz_attempts.aggregate(avg=Avg('score'))['avg'] or 0,
            'assignments_submitted': assignment_submissions.count(),
            'last_activity': StudentProgress.objects.filter(
                user=student,
                video_lesson__module__course=course
            ).order_by('-last_watched_at').first(),
        })
    
    # Monthly progress tracking
    monthly_data = []
    for i in range(6, 0, -1):  # Last 6 months
        month_start = timezone.now().replace(day=1) - timedelta(days=30*i)
        month_end = month_start + timedelta(days=30)
        
        videos = StudentProgress.objects.filter(
            user=student,
            last_watched_at__gte=month_start,
            last_watched_at__lt=month_end,
            completed=True
        ).count()
        
        quizzes = QuizAttempt.objects.filter(
            student=student,
            completed_at__gte=month_start,
            completed_at__lt=month_end
        ).count()
        
        assignments = AssignmentSubmission.objects.filter(
            student=student,
            created_at__gte=month_start,
            created_at__lt=month_end
        ).exclude(status='draft').count()
        
        month_progress = {
            'month': month_start.strftime('%b %Y'),
            'videos': videos,
            'quizzes': quizzes,
            'assignments': assignments,
            'videos_height': max(videos * 10 + 10, 2) if videos > 0 else 2,
            'quizzes_height': max(quizzes * 15 + 10, 2) if quizzes > 0 else 2,
            'assignments_height': max(assignments * 20 + 10, 2) if assignments > 0 else 2,
        }
        monthly_data.append(month_progress)
    
    context = {
        'analytics': analytics,
        'course_insights': course_insights,
        'monthly_data': monthly_data,
    }
    
    return render(request, 'student_portal/mentoring/progress_insights.html', context)