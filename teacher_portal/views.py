"""
Teacher Portal Views
Teachers can view their assigned courses, students, batches, and manage content
"""
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.auth import logout
from django.contrib import messages
from django.db.models import Count, Avg, Q, Sum
from django.core.paginator import Paginator
from django.utils import timezone
from django.http import JsonResponse
from datetime import timedelta, date

from apps.teachers.models import TeacherProfile, TeacherSchedule, TeacherAnnouncement
from apps.courses.models import (
    Course, Module, VideoLesson, Assignment, Quiz,
    AssignmentSubmission, QuizAttempt, StudentProgress
)
from apps.payments.models import Enrollment
from apps.users.models import User
from apps.live_sessions.models import LiveSession, SessionParticipant


def teacher_required(view_func):
    """Decorator to ensure user is a teacher"""
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect('landing:login')

        user_role = getattr(request.user, 'role', None)
        if user_role != 'teacher':
            messages.error(request, 'Access denied. Teacher account required.')
            return redirect('landing:login')

        # Check if teacher has a profile
        if not hasattr(request.user, 'teacher_profile'):
            messages.error(request, 'Teacher profile not found. Please contact admin.')
            return redirect('landing:login')

        return view_func(request, *args, **kwargs)
    return wrapper


def get_teacher_profile(user):
    """Get teacher profile for user"""
    try:
        return user.teacher_profile
    except TeacherProfile.DoesNotExist:
        return None


@login_required
@teacher_required
def dashboard(request):
    """Teacher dashboard - overview of assigned courses, students, and activity"""
    teacher = get_teacher_profile(request.user)

    # Get assigned courses
    assigned_courses = teacher.assigned_courses.filter(is_published=True)

    # Get all students enrolled in teacher's courses
    enrolled_students = Enrollment.objects.filter(
        course__in=assigned_courses,
        active=True
    ).select_related('user', 'course').order_by('-enrolled_on')

    total_students = enrolled_students.values('user').distinct().count()

    # Recent enrollments (last 7 days)
    week_ago = timezone.now() - timedelta(days=7)
    recent_enrollments = enrolled_students.filter(enrolled_on__gte=week_ago).count()

    # Pending assignments to grade
    pending_submissions = AssignmentSubmission.objects.filter(
        assignment__courses__in=assigned_courses,
        status='submitted'
    ).count()

    # Recent quiz attempts
    recent_quiz_attempts = QuizAttempt.objects.filter(
        quiz__courses__in=assigned_courses,
        completed=True
    ).order_by('-completed_at')[:5]

    # Average quiz scores
    avg_quiz_score = QuizAttempt.objects.filter(
        quiz__courses__in=assigned_courses,
        completed=True
    ).aggregate(avg=Avg('score'))['avg'] or 0

    # Get teacher's schedule for today
    today = timezone.now().strftime('%A').lower()
    todays_schedule = teacher.schedules.filter(
        day_of_week=today,
        is_active=True
    ).order_by('start_time')

    # Recent announcements
    my_announcements = teacher.announcements.order_by('-created_at')[:5]

    # Course-wise stats
    course_stats = []
    for course in assigned_courses[:5]:
        stats = {
            'course': course,
            'students': Enrollment.objects.filter(course=course, active=True).count(),
            'modules': course.modules.count(),
            'assignments': Assignment.objects.filter(courses=course).count(),
            'quizzes': Quiz.objects.filter(courses=course).count(),
        }
        course_stats.append(stats)

    context = {
        'teacher': teacher,
        'assigned_courses': assigned_courses,
        'total_courses': assigned_courses.count(),
        'total_students': total_students,
        'recent_enrollments': recent_enrollments,
        'pending_submissions': pending_submissions,
        'recent_quiz_attempts': recent_quiz_attempts,
        'avg_quiz_score': round(avg_quiz_score, 1),
        'todays_schedule': todays_schedule,
        'my_announcements': my_announcements,
        'course_stats': course_stats,
        'recent_students': enrolled_students[:5],
    }

    return render(request, 'teacher_portal/dashboard.html', context)


@login_required
@teacher_required
def my_courses(request):
    """List teacher's assigned courses"""
    teacher = get_teacher_profile(request.user)

    courses = teacher.assigned_courses.annotate(
        enrolled_count=Count('enrollments', filter=Q(enrollments__active=True)),
        module_count=Count('modules', distinct=True),
    ).order_by('title')

    # Calculate totals
    total_students = Enrollment.objects.filter(
        course__in=courses,
        active=True
    ).values('user').distinct().count()

    total_modules = sum(c.module_count for c in courses)
    total_assignments = Assignment.objects.filter(courses__in=courses).distinct().count()

    context = {
        'teacher': teacher,
        'courses': courses,
        'total_students': total_students,
        'total_modules': total_modules,
        'total_assignments': total_assignments,
    }

    return render(request, 'teacher_portal/courses.html', context)


@login_required
@teacher_required
def course_detail(request, course_id):
    """View details of a specific course"""
    teacher = get_teacher_profile(request.user)

    # Ensure teacher is assigned to this course
    course = get_object_or_404(
        teacher.assigned_courses,
        id=course_id
    )

    # Get enrolled students
    enrollments = Enrollment.objects.filter(
        course=course,
        active=True
    ).select_related('user').order_by('-enrolled_on')

    # Get modules with content counts
    modules = course.modules.annotate(
        video_count=Count('video_links', distinct=True),
    ).order_by('order')

    # Get assignments
    assignments = Assignment.objects.filter(courses=course)
    assignment_count = assignments.count()

    # Get quizzes
    quizzes = Quiz.objects.filter(courses=course)
    quiz_count = quizzes.count()

    # Pending submissions for this course
    pending_submissions = AssignmentSubmission.objects.filter(
        assignment__courses=course,
        status='submitted'
    ).select_related('student', 'assignment')
    pending_count = pending_submissions.count()

    # Recent submissions (for the table)
    recent_submissions = AssignmentSubmission.objects.filter(
        assignment__courses=course
    ).exclude(status='draft').select_related('student', 'assignment').order_by('-submitted_at')[:5]

    # Recent quiz attempts
    recent_attempts = QuizAttempt.objects.filter(
        quiz__courses=course,
        completed=True
    ).select_related('student', 'quiz').order_by('-completed_at')[:10]

    # Recent enrollments
    recent_enrollments = enrollments[:5]

    context = {
        'teacher': teacher,
        'course': course,
        'enrollments': enrollments,
        'enrollment_count': enrollments.count(),
        'modules': modules,
        'assignments': assignments,
        'assignment_count': assignment_count,
        'quizzes': quizzes,
        'quiz_count': quiz_count,
        'pending_submissions': pending_submissions,
        'pending_count': pending_count,
        'recent_submissions': recent_submissions,
        'recent_enrollments': recent_enrollments,
        'recent_attempts': recent_attempts,
        'total_students': enrollments.count(),
    }

    return render(request, 'teacher_portal/course_detail.html', context)


@login_required
@teacher_required
def my_students(request):
    """List all students enrolled in teacher's courses"""
    teacher = get_teacher_profile(request.user)
    assigned_courses = teacher.assigned_courses.all()

    # Get all enrollments for teacher's courses
    enrollments = Enrollment.objects.filter(
        course__in=assigned_courses,
        active=True
    ).select_related('user', 'course').order_by('-enrolled_on')

    # Course filter
    course_filter = request.GET.get('course', '')
    if course_filter:
        enrollments = enrollments.filter(course_id=course_filter)

    # Search filter
    search = request.GET.get('search', '')
    if search:
        enrollments = enrollments.filter(
            Q(user__name__icontains=search) |
            Q(user__email__icontains=search) |
            Q(user__phone_number__icontains=search)
        )

    # Stats
    total_students = enrollments.values('user').distinct().count()

    # Active this week (students with recent progress)
    week_ago = timezone.now() - timedelta(days=7)
    active_students = StudentProgress.objects.filter(
        course__in=assigned_courses,
        updated_at__gte=week_ago
    ).values('user').distinct().count()

    # New enrollments this month
    month_ago = timezone.now() - timedelta(days=30)
    new_enrollments = enrollments.filter(enrolled_on__gte=month_ago).count()

    # Average progress (placeholder - would need actual calculation)
    avg_progress = 0

    context = {
        'teacher': teacher,
        'enrollments': enrollments,
        'courses': assigned_courses,
        'selected_course': int(course_filter) if course_filter else None,
        'search': search,
        'total_students': total_students,
        'active_students': active_students,
        'avg_progress': avg_progress,
        'new_enrollments': new_enrollments,
    }

    return render(request, 'teacher_portal/students.html', context)


@login_required
@teacher_required
def student_detail(request, student_id):
    """View a specific student's progress in teacher's courses"""
    teacher = get_teacher_profile(request.user)
    assigned_courses = teacher.assigned_courses.all()

    # Ensure student is enrolled in one of teacher's courses
    student = get_object_or_404(User, id=student_id)

    enrollments = Enrollment.objects.filter(
        user=student,
        course__in=assigned_courses,
        active=True
    ).select_related('course')

    if not enrollments.exists():
        messages.error(request, 'This student is not enrolled in your courses.')
        return redirect('teacher_portal:my_students')

    # Assignment stats
    total_assignments = Assignment.objects.filter(courses__in=assigned_courses).distinct().count()
    completed_assignments = AssignmentSubmission.objects.filter(
        student=student,
        assignment__courses__in=assigned_courses,
        status='graded'
    ).count()

    # Quiz stats
    quiz_attempts = QuizAttempt.objects.filter(
        student=student,
        quiz__courses__in=assigned_courses,
        completed=True
    ).select_related('quiz').order_by('-completed_at')
    avg_quiz_score = quiz_attempts.aggregate(avg=Avg('score'))['avg'] or 0

    # Submissions
    submissions = AssignmentSubmission.objects.filter(
        student=student,
        assignment__courses__in=assigned_courses
    ).exclude(status='draft').select_related('assignment').order_by('-submitted_at')

    # Recent activity (simplified)
    recent_activity = []

    context = {
        'teacher': teacher,
        'student': student,
        'enrollments': enrollments,
        'total_assignments': total_assignments,
        'completed_assignments': completed_assignments,
        'avg_quiz_score': round(avg_quiz_score, 1),
        'total_watch_time': 0,  # Placeholder
        'submissions': submissions[:10],
        'quiz_attempts': quiz_attempts[:10],
        'recent_activity': recent_activity,
    }

    return render(request, 'teacher_portal/student_detail.html', context)


@login_required
@teacher_required
def assignments(request):
    """View assignments and submissions"""
    teacher = get_teacher_profile(request.user)
    assigned_courses = teacher.assigned_courses.all()

    # Get all submissions for teacher's courses
    all_submissions = AssignmentSubmission.objects.filter(
        assignment__courses__in=assigned_courses
    ).exclude(status='draft').select_related('student', 'assignment', 'assignment__courses')

    # Filters
    course_filter = request.GET.get('course', '')
    status_filter = request.GET.get('status', '')

    submissions = all_submissions
    if course_filter:
        submissions = submissions.filter(assignment__courses__id=course_filter)
    if status_filter == 'pending':
        submissions = submissions.filter(status='submitted')
    elif status_filter == 'graded':
        submissions = submissions.filter(status='graded')

    submissions = submissions.order_by('-submitted_at')

    # Stats
    total_assignments = Assignment.objects.filter(courses__in=assigned_courses).distinct().count()
    pending_count = all_submissions.filter(status='submitted').count()
    graded_count = all_submissions.filter(status='graded').count()
    avg_grade = all_submissions.filter(status='graded', score__isnull=False).aggregate(
        avg=Avg('score')
    )['avg'] or 0

    context = {
        'teacher': teacher,
        'submissions': submissions,
        'courses': assigned_courses,
        'total_assignments': total_assignments,
        'pending_count': pending_count,
        'graded_count': graded_count,
        'avg_grade': avg_grade,
    }

    return render(request, 'teacher_portal/assignments.html', context)


@login_required
@teacher_required
def assignment_submissions(request, assignment_id):
    """View submissions for a specific assignment"""
    teacher = get_teacher_profile(request.user)
    assigned_courses = teacher.assigned_courses.all()

    assignment = get_object_or_404(Assignment, id=assignment_id)

    # Check if assignment is in teacher's courses
    if not assignment.courses.filter(id__in=assigned_courses).exists():
        messages.error(request, 'You do not have access to this assignment.')
        return redirect('teacher_portal:assignments')

    submissions = AssignmentSubmission.objects.filter(
        assignment=assignment
    ).exclude(status='draft').select_related('student').order_by('-submitted_at')

    # Stats
    all_submissions = submissions
    pending_count = all_submissions.filter(status='submitted').count()
    graded_count = all_submissions.filter(status='graded').count()

    # Filter by status
    status_filter = request.GET.get('status', '')
    if status_filter:
        submissions = submissions.filter(status=status_filter)

    context = {
        'teacher': teacher,
        'assignment': assignment,
        'submissions': submissions,
        'status_filter': status_filter,
        'pending_count': pending_count,
        'graded_count': graded_count,
    }

    return render(request, 'teacher_portal/assignment_submissions.html', context)


@login_required
@teacher_required
def grade_submission(request, submission_id):
    """Grade an assignment submission"""
    teacher = get_teacher_profile(request.user)
    assigned_courses = teacher.assigned_courses.all()

    submission = get_object_or_404(
        AssignmentSubmission.objects.select_related('assignment', 'student'),
        id=submission_id
    )

    # Check access
    if not submission.assignment.courses.filter(id__in=assigned_courses).exists():
        messages.error(request, 'You do not have access to this submission.')
        return redirect('teacher_portal:assignments')

    if request.method == 'POST':
        score = request.POST.get('grade')
        feedback = request.POST.get('feedback', '')

        try:
            submission.score = int(score)
            submission.grade_comments = feedback
            submission.status = 'graded'
            submission.graded_by = request.user
            submission.graded_at = timezone.now()
            submission.save()

            messages.success(request, f'Submission graded successfully.')
            return redirect('teacher_portal:assignment_submissions', assignment_id=submission.assignment.id)
        except (ValueError, TypeError):
            messages.error(request, 'Invalid grade value.')

    context = {
        'teacher': teacher,
        'submission': submission,
    }

    return render(request, 'teacher_portal/grade_submission.html', context)


@login_required
@teacher_required
def quizzes(request):
    """View quizzes and attempts"""
    teacher = get_teacher_profile(request.user)
    assigned_courses = teacher.assigned_courses.all()

    quizzes_list = Quiz.objects.filter(
        courses__in=assigned_courses
    ).annotate(
        attempts_count=Count('attempts', filter=Q(attempts__completed=True)),
        avg_score=Avg('attempts__score', filter=Q(attempts__completed=True)),
        pass_count=Count('attempts', filter=Q(attempts__completed=True, attempts__score__gte=60))
    ).distinct().order_by('-created_at')

    # Course filter
    course_filter = request.GET.get('course', '')
    if course_filter:
        quizzes_list = quizzes_list.filter(courses__id=course_filter)

    # Stats
    total_quizzes = quizzes_list.count()
    total_attempts = sum(q.attempts_count for q in quizzes_list)
    avg_score = QuizAttempt.objects.filter(
        quiz__courses__in=assigned_courses,
        completed=True
    ).aggregate(avg=Avg('score'))['avg'] or 0

    # Pass rate
    pass_rate = 0
    if total_attempts > 0:
        total_passes = sum(q.pass_count for q in quizzes_list)
        pass_rate = (total_passes / total_attempts) * 100

    context = {
        'teacher': teacher,
        'quizzes': quizzes_list,
        'courses': assigned_courses,
        'total_quizzes': total_quizzes,
        'total_attempts': total_attempts,
        'avg_score': avg_score,
        'pass_rate': pass_rate,
    }

    return render(request, 'teacher_portal/quizzes.html', context)


@login_required
@teacher_required
def quiz_attempts(request, quiz_id):
    """View attempts for a specific quiz"""
    teacher = get_teacher_profile(request.user)
    assigned_courses = teacher.assigned_courses.all()

    quiz = get_object_or_404(Quiz, id=quiz_id)

    # Check access
    if not quiz.courses.filter(id__in=assigned_courses).exists():
        messages.error(request, 'You do not have access to this quiz.')
        return redirect('teacher_portal:quizzes')

    attempts = QuizAttempt.objects.filter(
        quiz=quiz,
        completed=True
    ).select_related('student').order_by('-completed_at')

    # Calculate score percentage for each attempt
    for attempt in attempts:
        total_marks = getattr(quiz, 'total_marks', quiz.questions.count())
        if total_marks > 0:
            attempt.score_percentage = (attempt.score / total_marks) * 100
        else:
            attempt.score_percentage = 0

    # Stats
    passing_score = getattr(quiz, 'passing_score', 50)
    avg_score = attempts.aggregate(avg=Avg('score'))['avg'] or 0
    total_marks = getattr(quiz, 'total_marks', quiz.questions.count())
    avg_percentage = (avg_score / total_marks * 100) if total_marks > 0 else 0

    # Score distribution
    excellent_count = sum(1 for a in attempts if a.score_percentage >= 90)
    good_count = sum(1 for a in attempts if 70 <= a.score_percentage < 90)
    average_count = sum(1 for a in attempts if 50 <= a.score_percentage < 70)
    poor_count = sum(1 for a in attempts if a.score_percentage < 50)

    pass_count = sum(1 for a in attempts if a.score_percentage >= passing_score)
    pass_rate = (pass_count / len(attempts) * 100) if attempts else 0

    context = {
        'teacher': teacher,
        'quiz': quiz,
        'attempts': attempts,
        'avg_score': avg_percentage,
        'pass_rate': pass_rate,
        'excellent_count': excellent_count,
        'good_count': good_count,
        'average_count': average_count,
        'poor_count': poor_count,
    }

    return render(request, 'teacher_portal/quiz_attempts.html', context)


@login_required
@teacher_required
def my_schedule(request):
    """View teacher's schedule"""
    teacher = get_teacher_profile(request.user)

    schedules = teacher.schedules.filter(is_active=True).order_by(
        'day_of_week', 'start_time'
    ).select_related('course', 'batch')

    # Group by day
    schedule_by_day = {}
    days_order = ['monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday', 'sunday']

    for day in days_order:
        day_schedules = [s for s in schedules if s.day_of_week == day]
        if day_schedules:
            schedule_by_day[day] = day_schedules

    context = {
        'teacher': teacher,
        'schedule_by_day': schedule_by_day,
    }

    return render(request, 'teacher_portal/schedule.html', context)


@login_required
@teacher_required
def announcements(request):
    """View and create announcements"""
    teacher = get_teacher_profile(request.user)

    my_announcements = teacher.announcements.order_by('-created_at')

    if request.method == 'POST':
        title = request.POST.get('title')
        content = request.POST.get('content')
        course_id = request.POST.get('course')
        is_global = request.POST.get('is_global') == 'on'

        if title and content:
            announcement = TeacherAnnouncement.objects.create(
                teacher=teacher,
                title=title,
                content=content,
                is_global=is_global
            )

            if course_id and not is_global:
                try:
                    course = teacher.assigned_courses.get(id=course_id)
                    announcement.course = course
                    announcement.save()
                except:
                    pass

            messages.success(request, 'Announcement created successfully.')
            return redirect('teacher_portal:announcements')

    context = {
        'teacher': teacher,
        'announcements': my_announcements,
        'assigned_courses': teacher.assigned_courses.all(),
    }

    return render(request, 'teacher_portal/announcements.html', context)


@login_required
@teacher_required
def my_profile(request):
    """View/edit teacher profile"""
    teacher = get_teacher_profile(request.user)
    assigned_courses = teacher.assigned_courses.all()

    # Stats
    total_students = Enrollment.objects.filter(
        course__in=assigned_courses,
        active=True
    ).values('user').distinct().count()

    graded_assignments = AssignmentSubmission.objects.filter(
        assignment__courses__in=assigned_courses,
        graded_by=request.user
    ).count()

    total_announcements = teacher.announcements.count()

    context = {
        'teacher': teacher,
        'assigned_courses': assigned_courses[:6],
        'total_courses': assigned_courses.count(),
        'total_students': total_students,
        'graded_assignments': graded_assignments,
        'total_announcements': total_announcements,
    }

    return render(request, 'teacher_portal/profile.html', context)


@login_required
@teacher_required
def update_profile(request):
    """Update teacher profile"""
    if request.method == 'POST':
        user = request.user
        teacher = get_teacher_profile(user)

        # Update user info
        name = request.POST.get('name', '').strip()
        phone = request.POST.get('phone_number', '').strip()

        if name:
            user.name = name
        if phone:
            user.phone_number = phone
        user.save()

        messages.success(request, 'Profile updated successfully.')

    return redirect('teacher_portal:my_profile')


@login_required
@teacher_required
def change_password(request):
    """Change password"""
    if request.method == 'POST':
        user = request.user
        current_password = request.POST.get('current_password')
        new_password = request.POST.get('new_password')
        confirm_password = request.POST.get('confirm_password')

        if not user.check_password(current_password):
            messages.error(request, 'Current password is incorrect.')
        elif new_password != confirm_password:
            messages.error(request, 'New passwords do not match.')
        elif len(new_password) < 8:
            messages.error(request, 'Password must be at least 8 characters.')
        else:
            user.set_password(new_password)
            user.save()
            messages.success(request, 'Password changed successfully. Please log in again.')
            return redirect('landing:login')

    return redirect('teacher_portal:my_profile')


@login_required
@teacher_required
def course_students(request, course_id):
    """View students enrolled in a specific course"""
    teacher = get_teacher_profile(request.user)

    course = get_object_or_404(
        teacher.assigned_courses,
        id=course_id
    )

    enrollments = Enrollment.objects.filter(
        course=course,
        active=True
    ).select_related('user').order_by('-enrolled_on')

    # Search
    search = request.GET.get('search', '')
    if search:
        enrollments = enrollments.filter(
            Q(user__name__icontains=search) |
            Q(user__email__icontains=search)
        )

    context = {
        'teacher': teacher,
        'course': course,
        'enrollments': enrollments,
        'search': search,
        'total_students': enrollments.count(),
    }

    return render(request, 'teacher_portal/course_students.html', context)


@login_required
@teacher_required
def course_assignments(request, course_id):
    """View assignments for a specific course"""
    teacher = get_teacher_profile(request.user)

    course = get_object_or_404(
        teacher.assigned_courses,
        id=course_id
    )

    assignments_list = Assignment.objects.filter(
        courses=course
    ).annotate(
        submission_count=Count('submissions', distinct=True),
        pending_count=Count('submissions', filter=Q(submissions__status='submitted'))
    ).order_by('-created_at')

    context = {
        'teacher': teacher,
        'course': course,
        'assignments': assignments_list,
    }

    return render(request, 'teacher_portal/course_assignments.html', context)


@login_required
@teacher_required
def course_quizzes(request, course_id):
    """View quizzes for a specific course"""
    teacher = get_teacher_profile(request.user)

    course = get_object_or_404(
        teacher.assigned_courses,
        id=course_id
    )

    quizzes_list = Quiz.objects.filter(
        courses=course
    ).annotate(
        attempt_count=Count('attempts', filter=Q(attempts__completed=True)),
        avg_score=Avg('attempts__score', filter=Q(attempts__completed=True))
    ).order_by('-created_at')

    context = {
        'teacher': teacher,
        'course': course,
        'quizzes': quizzes_list,
    }

    return render(request, 'teacher_portal/course_quizzes.html', context)


@login_required
@teacher_required
def create_announcement(request):
    """Create a new announcement"""
    teacher = get_teacher_profile(request.user)

    if request.method == 'POST':
        title = request.POST.get('title', '').strip()
        content = request.POST.get('content', '').strip()
        course_id = request.POST.get('course')
        is_pinned = request.POST.get('is_pinned') == 'on'
        expiry_date = request.POST.get('expiry_date')

        if title and content:
            announcement = TeacherAnnouncement.objects.create(
                teacher=teacher,
                title=title,
                content=content,
                is_pinned=is_pinned
            )

            if course_id:
                try:
                    course = teacher.assigned_courses.get(id=course_id)
                    announcement.course = course
                    announcement.save()
                except:
                    pass

            if expiry_date:
                try:
                    from datetime import datetime
                    announcement.expiry_date = datetime.strptime(expiry_date, '%Y-%m-%dT%H:%M')
                    announcement.save()
                except:
                    pass

            messages.success(request, 'Announcement created successfully.')
            return redirect('teacher_portal:announcements')
        else:
            messages.error(request, 'Title and content are required.')

    context = {
        'teacher': teacher,
        'courses': teacher.assigned_courses.all(),
    }

    return render(request, 'teacher_portal/announcement_form.html', context)


@login_required
@teacher_required
def edit_announcement(request, announcement_id):
    """Edit an existing announcement"""
    teacher = get_teacher_profile(request.user)

    announcement = get_object_or_404(
        TeacherAnnouncement,
        id=announcement_id,
        teacher=teacher
    )

    if request.method == 'POST':
        title = request.POST.get('title', '').strip()
        content = request.POST.get('content', '').strip()
        course_id = request.POST.get('course')
        is_pinned = request.POST.get('is_pinned') == 'on'
        expiry_date = request.POST.get('expiry_date')

        if title and content:
            announcement.title = title
            announcement.content = content
            announcement.is_pinned = is_pinned

            if course_id:
                try:
                    course = teacher.assigned_courses.get(id=course_id)
                    announcement.course = course
                except:
                    announcement.course = None
            else:
                announcement.course = None

            if expiry_date:
                try:
                    from datetime import datetime
                    announcement.expiry_date = datetime.strptime(expiry_date, '%Y-%m-%dT%H:%M')
                except:
                    pass
            else:
                announcement.expiry_date = None

            announcement.save()
            messages.success(request, 'Announcement updated successfully.')
            return redirect('teacher_portal:announcements')
        else:
            messages.error(request, 'Title and content are required.')

    context = {
        'teacher': teacher,
        'announcement': announcement,
        'courses': teacher.assigned_courses.all(),
    }

    return render(request, 'teacher_portal/announcement_form.html', context)


@login_required
@teacher_required
def delete_announcement(request, announcement_id):
    """Delete an announcement"""
    teacher = get_teacher_profile(request.user)

    announcement = get_object_or_404(
        TeacherAnnouncement,
        id=announcement_id,
        teacher=teacher
    )

    if request.method == 'POST':
        announcement.delete()
        messages.success(request, 'Announcement deleted successfully.')

    return redirect('teacher_portal:announcements')


def teacher_logout(request):
    """Teacher logout with cache clearing"""
    logout(request)
    messages.success(request, 'You have been logged out successfully.')
    response = redirect('landing:login')
    # Add headers to prevent caching
    response['Cache-Control'] = 'no-cache, no-store, must-revalidate, max-age=0'
    response['Pragma'] = 'no-cache'
    response['Expires'] = '0'
    return response


# =============================================================================
# LIVE SESSIONS
# =============================================================================

@login_required
@teacher_required
def live_sessions(request):
    """View all live sessions for teacher's courses"""
    teacher = get_teacher_profile(request.user)

    # Get all courses assigned to teacher (via M2M and FK)
    assigned_courses_m2m = teacher.assigned_courses.all()
    assigned_courses_fk = Course.objects.filter(teacher=teacher)
    all_teacher_courses = Course.objects.filter(
        Q(id__in=assigned_courses_m2m) | Q(teacher=teacher)
    ).distinct()

    # Get live sessions for these courses
    sessions = LiveSession.objects.filter(
        course__in=all_teacher_courses
    ).select_related('course', 'created_by').order_by('-scheduled_date')

    # Filter by status
    status_filter = request.GET.get('status', '')
    if status_filter:
        sessions = sessions.filter(status=status_filter)

    # Categorize sessions
    now = timezone.now()
    upcoming_sessions = sessions.filter(scheduled_date__gte=now, status='scheduled')
    live_now = sessions.filter(status='live')
    past_sessions = sessions.filter(Q(scheduled_date__lt=now) | Q(status='ended'))

    # Pagination for past sessions
    paginator = Paginator(past_sessions, 10)
    page = request.GET.get('page', 1)
    past_sessions_page = paginator.get_page(page)

    context = {
        'page_title': 'Live Sessions',
        'upcoming_sessions': upcoming_sessions[:10],
        'live_now': live_now,
        'past_sessions': past_sessions_page,
        'status_filter': status_filter,
        'total_upcoming': upcoming_sessions.count(),
        'total_live': live_now.count(),
        'total_past': past_sessions.count(),
    }

    return render(request, 'teacher_portal/live_sessions/list.html', context)


@login_required
@teacher_required
def live_session_detail(request, session_id):
    """View details of a specific live session"""
    teacher = get_teacher_profile(request.user)

    # Get all courses assigned to teacher
    all_teacher_courses = Course.objects.filter(
        Q(id__in=teacher.assigned_courses.all()) | Q(teacher=teacher)
    ).distinct()

    # Get the session - ensure it belongs to teacher's courses
    session = get_object_or_404(
        LiveSession.objects.select_related('course', 'created_by'),
        id=session_id,
        course__in=all_teacher_courses
    )

    # Get participants
    participants = SessionParticipant.objects.filter(
        session=session
    ).select_related('student').order_by('student__name')

    # Attendance stats
    total_assigned = participants.count()
    attended = participants.filter(status='attended').count()
    missed = participants.filter(status='missed').count()

    context = {
        'page_title': f'Session: {session.title}',
        'session': session,
        'participants': participants,
        'total_assigned': total_assigned,
        'attended': attended,
        'missed': missed,
        'attendance_rate': (attended / total_assigned * 100) if total_assigned > 0 else 0,
    }

    return render(request, 'teacher_portal/live_sessions/detail.html', context)
