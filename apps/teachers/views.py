from rest_framework import status, generics, permissions
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.decorators import api_view, permission_classes
from rest_framework_simplejwt.tokens import RefreshToken
from django.contrib.auth import authenticate, get_user_model
from django.utils import timezone
from django.db.models import Count, Q, Avg
from django.shortcuts import get_object_or_404

from .models import TeacherProfile, TeacherSchedule, TeacherAnnouncement
from .serializers import (
    TeacherLoginSerializer, TeacherChangePasswordSerializer,
    TeacherForgotPasswordSerializer, TeacherResetPasswordSerializer,
    TeacherProfileSerializer, TeacherProfileUpdateSerializer,
    TeacherCourseListSerializer, TeacherStudentSerializer, StudentDetailSerializer,
    AssignmentSubmissionListSerializer, GradeSubmissionSerializer,
    QuizAttemptListSerializer, TeacherScheduleSerializer,
    TeacherAnnouncementSerializer, TeacherAnnouncementCreateSerializer,
    TeacherDashboardSerializer, AdminTeacherCreateSerializer,
    AdminTeacherUpdateSerializer, AdminTeacherListSerializer,
    AssignCoursesSerializer
)
from .permissions import IsTeacher, IsTeacherOrAdmin

User = get_user_model()


# ============== Authentication APIs ==============

class TeacherLoginView(APIView):
    """
    Teacher login API.
    Returns JWT tokens if credentials are valid and user is a teacher.
    """
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        serializer = TeacherLoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        email = serializer.validated_data['email']
        password = serializer.validated_data['password']

        # Check if user exists
        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            return Response(
                {'error': 'Invalid email or password'},
                status=status.HTTP_401_UNAUTHORIZED
            )

        # Check if user is a teacher
        if user.role != 'teacher':
            return Response(
                {'error': 'Access denied. This login is for teachers only.'},
                status=status.HTTP_403_FORBIDDEN
            )

        # Check if user is active
        if not user.is_active:
            return Response(
                {'error': 'Your account has been deactivated. Please contact admin.'},
                status=status.HTTP_403_FORBIDDEN
            )

        # Authenticate
        authenticated_user = authenticate(email=email, password=password)
        if authenticated_user is None:
            return Response(
                {'error': 'Invalid email or password'},
                status=status.HTTP_401_UNAUTHORIZED
            )

        # Generate tokens
        refresh = RefreshToken.for_user(authenticated_user)

        # Add custom claims
        refresh['role'] = authenticated_user.role
        refresh['name'] = authenticated_user.name
        refresh['user_id'] = authenticated_user.id

        # Get teacher profile
        try:
            teacher_profile = authenticated_user.teacher_profile
            must_change_password = teacher_profile.must_change_password
        except TeacherProfile.DoesNotExist:
            must_change_password = True

        return Response({
            'access': str(refresh.access_token),
            'refresh': str(refresh),
            'user': {
                'id': authenticated_user.id,
                'email': authenticated_user.email,
                'name': authenticated_user.name,
                'role': authenticated_user.role,
            },
            'must_change_password': must_change_password
        })


class TeacherChangePasswordView(APIView):
    """Change password for authenticated teacher"""
    permission_classes = [IsTeacher]

    def post(self, request):
        serializer = TeacherChangePasswordSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        user = request.user
        teacher_profile = user.teacher_profile

        # If must_change_password is True, don't require old password
        if not teacher_profile.must_change_password:
            old_password = serializer.validated_data.get('old_password')
            if not old_password:
                return Response(
                    {'error': 'Current password is required'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            if not user.check_password(old_password):
                return Response(
                    {'error': 'Current password is incorrect'},
                    status=status.HTTP_400_BAD_REQUEST
                )

        # Set new password
        user.set_password(serializer.validated_data['new_password'])
        user.save()

        # Update profile
        teacher_profile.must_change_password = False
        teacher_profile.last_password_change = timezone.now()
        teacher_profile.save()

        return Response({'message': 'Password changed successfully'})


class TeacherForgotPasswordView(APIView):
    """Request password reset code"""
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        serializer = TeacherForgotPasswordSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        email = serializer.validated_data['email']

        try:
            user = User.objects.get(email=email, role='teacher')

            # Create password reset code
            from apps.users.models import PasswordResetCode
            code = PasswordResetCode.objects.create(user=user)

            # Send email (using existing email service)
            # TODO: Implement email sending

            return Response({
                'message': 'If an account exists with this email, a reset code has been sent.'
            })
        except User.DoesNotExist:
            # Return same message for security
            return Response({
                'message': 'If an account exists with this email, a reset code has been sent.'
            })


class TeacherResetPasswordView(APIView):
    """Reset password with verification code"""
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        serializer = TeacherResetPasswordSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        email = serializer.validated_data['email']
        code = serializer.validated_data['code']
        new_password = serializer.validated_data['new_password']

        try:
            user = User.objects.get(email=email, role='teacher')
            from apps.users.models import PasswordResetCode
            reset_code = PasswordResetCode.objects.filter(
                user=user,
                code=code,
                is_used=False
            ).latest('created_at')

            if not reset_code.is_valid():
                return Response(
                    {'error': 'Reset code has expired'},
                    status=status.HTTP_400_BAD_REQUEST
                )

            # Reset password
            user.set_password(new_password)
            user.save()

            # Mark code as used
            reset_code.is_used = True
            reset_code.save()

            # Update teacher profile
            try:
                teacher_profile = user.teacher_profile
                teacher_profile.must_change_password = False
                teacher_profile.last_password_change = timezone.now()
                teacher_profile.save()
            except TeacherProfile.DoesNotExist:
                pass

            return Response({'message': 'Password reset successfully'})

        except (User.DoesNotExist, PasswordResetCode.DoesNotExist):
            return Response(
                {'error': 'Invalid email or reset code'},
                status=status.HTTP_400_BAD_REQUEST
            )


# ============== Profile APIs ==============

class TeacherProfileView(APIView):
    """Get or update teacher profile"""
    permission_classes = [IsTeacher]

    def get(self, request):
        try:
            profile = request.user.teacher_profile
            serializer = TeacherProfileSerializer(profile)
            return Response(serializer.data)
        except TeacherProfile.DoesNotExist:
            return Response(
                {'error': 'Teacher profile not found'},
                status=status.HTTP_404_NOT_FOUND
            )

    def put(self, request):
        try:
            profile = request.user.teacher_profile
            serializer = TeacherProfileUpdateSerializer(profile, data=request.data, partial=True)
            serializer.is_valid(raise_exception=True)
            serializer.save()
            return Response(TeacherProfileSerializer(profile).data)
        except TeacherProfile.DoesNotExist:
            return Response(
                {'error': 'Teacher profile not found'},
                status=status.HTTP_404_NOT_FOUND
            )


# ============== Dashboard APIs ==============

class TeacherDashboardView(APIView):
    """Get teacher dashboard data"""
    permission_classes = [IsTeacher]

    def get(self, request):
        try:
            profile = request.user.teacher_profile
        except TeacherProfile.DoesNotExist:
            return Response(
                {'error': 'Teacher profile not found'},
                status=status.HTTP_404_NOT_FOUND
            )

        # Get assigned courses
        assigned_courses = profile.assigned_courses.all()

        # Get total students
        from apps.payments.models import Enrollment
        total_students = Enrollment.objects.filter(
            course__in=assigned_courses,
            active=True
        ).values('user').distinct().count()

        # Get pending assignments
        from apps.courses.models import AssignmentSubmission, Assignment
        pending_assignments = AssignmentSubmission.objects.filter(
            assignment__courses__in=assigned_courses,
            status='submitted'
        ).count()

        # Add assignments from modules of assigned courses
        pending_assignments += AssignmentSubmission.objects.filter(
            assignment__modules__course_links__course__in=assigned_courses,
            status='submitted'
        ).distinct().count()

        # Get recent submissions
        recent_submissions = AssignmentSubmission.objects.filter(
            Q(assignment__courses__in=assigned_courses) |
            Q(assignment__modules__course_links__course__in=assigned_courses)
        ).select_related('student', 'assignment').order_by('-submitted_at')[:5]

        recent_submissions_data = [{
            'id': s.id,
            'student_name': s.student.name,
            'assignment_title': s.assignment.title,
            'status': s.status,
            'submitted_at': s.submitted_at
        } for s in recent_submissions]

        # Get upcoming sessions for courses where teacher is assigned (via FK or M2M)
        from apps.live_sessions.models import LiveSession
        from apps.courses.models import Course
        # Combine courses assigned via M2M and courses where teacher is primary (FK)
        all_teacher_courses = Course.objects.filter(
            Q(teacher=profile) | Q(id__in=assigned_courses)
        ).distinct()
        upcoming_sessions = LiveSession.objects.filter(
            course__in=all_teacher_courses,
            scheduled_date__gte=timezone.now(),
            status='scheduled'
        ).order_by('scheduled_date')[:5]

        upcoming_sessions_data = [{
            'id': s.id,
            'title': s.title,
            'course_title': s.course.title if s.course else 'N/A',
            'scheduled_date': s.scheduled_date,
            'meeting_link': s.meeting_link,
            'duration_minutes': s.duration_minutes
        } for s in upcoming_sessions]

        # Get announcements count
        announcements_count = profile.announcements.filter(is_active=True).count()

        return Response({
            'total_courses': assigned_courses.count(),
            'total_students': total_students,
            'pending_assignments': pending_assignments,
            'pending_quizzes': 0,  # Quizzes are auto-graded
            'recent_submissions': recent_submissions_data,
            'upcoming_sessions': upcoming_sessions_data,
            'announcements_count': announcements_count
        })


# ============== Course APIs ==============

class TeacherCourseListView(APIView):
    """List courses assigned to teacher"""
    permission_classes = [IsTeacher]

    def get(self, request):
        try:
            profile = request.user.teacher_profile
            courses = profile.assigned_courses.select_related('category').all()
            serializer = TeacherCourseListSerializer(courses, many=True)
            return Response(serializer.data)
        except TeacherProfile.DoesNotExist:
            return Response([])


class TeacherCourseDetailView(APIView):
    """Get details of a specific course"""
    permission_classes = [IsTeacher]

    def get(self, request, course_id):
        try:
            profile = request.user.teacher_profile
            course = profile.assigned_courses.get(id=course_id)

            from apps.payments.models import Enrollment
            enrollments = Enrollment.objects.filter(course=course, active=True)

            # Get modules
            modules = course.module_links.select_related('module').order_by('order')
            modules_data = []
            for link in modules:
                module = link.module
                modules_data.append({
                    'id': module.id,
                    'title': module.title,
                    'order': link.order,
                    'video_count': module.video_links.count(),
                    'assignment_count': module.assignment_links.count(),
                    'quiz_count': module.quiz_links.count(),
                })

            return Response({
                'id': course.id,
                'title': course.title,
                'description': course.description,
                'category': course.category.name if course.category else None,
                'thumbnail': course.thumbnail.url if course.thumbnail else None,
                'is_published': course.is_published,
                'total_students': enrollments.count(),
                'modules': modules_data
            })
        except TeacherProfile.DoesNotExist:
            return Response(
                {'error': 'Teacher profile not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        except:
            return Response(
                {'error': 'Course not found or not assigned to you'},
                status=status.HTTP_404_NOT_FOUND
            )


class TeacherCourseStudentsView(APIView):
    """List students enrolled in a course"""
    permission_classes = [IsTeacher]

    def get(self, request, course_id):
        try:
            profile = request.user.teacher_profile
            course = profile.assigned_courses.get(id=course_id)

            from apps.payments.models import Enrollment
            from apps.courses.models import StudentProgress

            enrollments = Enrollment.objects.filter(
                course=course,
                active=True
            ).select_related('user')

            students_data = []
            for enrollment in enrollments:
                # Calculate progress
                total_videos = course.module_links.aggregate(
                    total=Count('module__video_links')
                )['total'] or 0

                completed_videos = StudentProgress.objects.filter(
                    user=enrollment.user,
                    course=course,
                    completed=True
                ).count()

                progress = (completed_videos / total_videos * 100) if total_videos > 0 else 0

                students_data.append({
                    'id': enrollment.user.id,
                    'name': enrollment.user.name,
                    'email': enrollment.user.email,
                    'phone_number': enrollment.user.phone_number,
                    'enrolled_at': enrollment.created_at,
                    'course_title': course.title,
                    'course_id': course.id,
                    'progress_percentage': round(progress, 2)
                })

            return Response(students_data)

        except Exception as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_404_NOT_FOUND
            )


# ============== Student APIs ==============

class TeacherAllStudentsView(APIView):
    """List all students across teacher's courses"""
    permission_classes = [IsTeacher]

    def get(self, request):
        try:
            profile = request.user.teacher_profile
            assigned_courses = profile.assigned_courses.all()

            from apps.payments.models import Enrollment
            enrollments = Enrollment.objects.filter(
                course__in=assigned_courses,
                active=True
            ).select_related('user', 'course').order_by('-created_at')

            students_data = []
            seen_users = set()

            for enrollment in enrollments:
                if enrollment.user.id not in seen_users:
                    seen_users.add(enrollment.user.id)
                    students_data.append({
                        'id': enrollment.user.id,
                        'name': enrollment.user.name,
                        'email': enrollment.user.email,
                        'phone_number': enrollment.user.phone_number,
                        'enrolled_at': enrollment.created_at,
                        'course_title': enrollment.course.title,
                        'course_id': enrollment.course.id,
                        'progress_percentage': 0
                    })

            return Response(students_data)

        except TeacherProfile.DoesNotExist:
            return Response([])


class TeacherStudentDetailView(APIView):
    """Get detailed student information"""
    permission_classes = [IsTeacher]

    def get(self, request, student_id):
        try:
            profile = request.user.teacher_profile
            assigned_courses = profile.assigned_courses.all()

            # Verify student is enrolled in teacher's courses
            from apps.payments.models import Enrollment
            enrollment = Enrollment.objects.filter(
                user_id=student_id,
                course__in=assigned_courses,
                active=True
            ).first()

            if not enrollment:
                return Response(
                    {'error': 'Student not found in your courses'},
                    status=status.HTTP_404_NOT_FOUND
                )

            student = enrollment.user
            serializer = StudentDetailSerializer(
                student,
                context={'teacher': profile}
            )
            return Response(serializer.data)

        except Exception as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_404_NOT_FOUND
            )


class TeacherStudentProgressView(APIView):
    """Get student's progress in teacher's courses"""
    permission_classes = [IsTeacher]

    def get(self, request, student_id):
        try:
            profile = request.user.teacher_profile
            assigned_courses = profile.assigned_courses.all()

            from apps.payments.models import Enrollment
            from apps.courses.models import StudentProgress, ModuleProgress

            # Get enrollments
            enrollments = Enrollment.objects.filter(
                user_id=student_id,
                course__in=assigned_courses,
                active=True
            ).select_related('course')

            progress_data = []
            for enrollment in enrollments:
                course = enrollment.course

                # Video progress
                total_videos = course.module_links.aggregate(
                    total=Count('module__video_links')
                )['total'] or 0

                completed_videos = StudentProgress.objects.filter(
                    user_id=student_id,
                    course=course,
                    completed=True
                ).count()

                # Module progress
                module_progress = ModuleProgress.objects.filter(
                    student_id=student_id,
                    module__course_links__course=course
                )

                progress_data.append({
                    'course_id': course.id,
                    'course_title': course.title,
                    'enrolled_at': enrollment.created_at,
                    'total_videos': total_videos,
                    'completed_videos': completed_videos,
                    'video_progress': round((completed_videos / total_videos * 100) if total_videos > 0 else 0, 2),
                    'modules_completed': module_progress.filter(is_completed=True).count(),
                    'total_modules': course.module_links.count()
                })

            return Response(progress_data)

        except Exception as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )


# ============== Assignment APIs ==============

class TeacherAssignmentListView(APIView):
    """List all assignments from teacher's courses"""
    permission_classes = [IsTeacher]

    def get(self, request):
        try:
            profile = request.user.teacher_profile
            assigned_courses = profile.assigned_courses.all()

            from apps.courses.models import Assignment

            # Get assignments linked to courses
            course_assignments = Assignment.objects.filter(
                courses__in=assigned_courses
            ).distinct()

            # Get assignments from modules of assigned courses
            module_assignments = Assignment.objects.filter(
                modules__course_links__course__in=assigned_courses
            ).distinct()

            # Combine
            assignments = (course_assignments | module_assignments).distinct()

            assignments_data = []
            for assignment in assignments:
                assignments_data.append({
                    'id': assignment.id,
                    'title': assignment.title,
                    'max_points': assignment.max_points,
                    'passing_score': assignment.passing_score,
                    'is_required': assignment.is_required,
                    'pending_count': assignment.submissions.filter(status='submitted').count(),
                    'graded_count': assignment.submissions.filter(status='graded').count()
                })

            return Response(assignments_data)

        except TeacherProfile.DoesNotExist:
            return Response([])


class TeacherAssignmentSubmissionsView(APIView):
    """List submissions for an assignment"""
    permission_classes = [IsTeacher]

    def get(self, request, assignment_id):
        try:
            profile = request.user.teacher_profile
            from apps.courses.models import Assignment, AssignmentSubmission

            assignment = Assignment.objects.get(id=assignment_id)

            # Verify teacher has access
            assigned_courses = profile.assigned_courses.all()
            has_access = (
                assignment.courses.filter(id__in=assigned_courses).exists() or
                assignment.modules.filter(course_links__course__in=assigned_courses).exists()
            )

            if not has_access:
                return Response(
                    {'error': 'You do not have access to this assignment'},
                    status=status.HTTP_403_FORBIDDEN
                )

            status_filter = request.query_params.get('status')
            submissions = assignment.submissions.select_related('student')

            if status_filter:
                submissions = submissions.filter(status=status_filter)

            submissions_data = []
            for s in submissions:
                course = assignment.get_first_course()
                submissions_data.append({
                    'id': s.id,
                    'student_id': s.student.id,
                    'student_name': s.student.name,
                    'student_email': s.student.email,
                    'assignment_id': assignment.id,
                    'assignment_title': assignment.title,
                    'course_title': course.title if course else '',
                    'github_url': s.github_url,
                    'submission_notes': s.submission_notes,
                    'status': s.status,
                    'score': s.score,
                    'max_points': assignment.max_points,
                    'submitted_at': s.submitted_at,
                    'graded_at': s.graded_at
                })

            return Response(submissions_data)

        except Assignment.DoesNotExist:
            return Response(
                {'error': 'Assignment not found'},
                status=status.HTTP_404_NOT_FOUND
            )


class TeacherGradeSubmissionView(APIView):
    """Grade an assignment submission"""
    permission_classes = [IsTeacher]

    def post(self, request, submission_id):
        try:
            profile = request.user.teacher_profile
            from apps.courses.models import AssignmentSubmission

            submission = AssignmentSubmission.objects.select_related('assignment').get(id=submission_id)
            assignment = submission.assignment

            # Verify teacher has access
            assigned_courses = profile.assigned_courses.all()
            has_access = (
                assignment.courses.filter(id__in=assigned_courses).exists() or
                assignment.modules.filter(course_links__course__in=assigned_courses).exists()
            )

            if not has_access:
                return Response(
                    {'error': 'You do not have access to this submission'},
                    status=status.HTTP_403_FORBIDDEN
                )

            serializer = GradeSubmissionSerializer(
                data=request.data,
                context={'submission': submission}
            )
            serializer.is_valid(raise_exception=True)

            # Grade the submission
            submission.grade(
                score=serializer.validated_data['score'],
                comments=serializer.validated_data.get('grade_comments', ''),
                graded_by=request.user
            )

            return Response({
                'message': 'Submission graded successfully',
                'score': submission.score,
                'is_passed': submission.is_passed
            })

        except AssignmentSubmission.DoesNotExist:
            return Response(
                {'error': 'Submission not found'},
                status=status.HTTP_404_NOT_FOUND
            )


# ============== Quiz APIs ==============

class TeacherQuizListView(APIView):
    """List all quizzes from teacher's courses"""
    permission_classes = [IsTeacher]

    def get(self, request):
        try:
            profile = request.user.teacher_profile
            assigned_courses = profile.assigned_courses.all()

            from apps.courses.models import Quiz

            # Get quizzes linked to courses
            course_quizzes = Quiz.objects.filter(
                courses__in=assigned_courses
            ).distinct()

            # Get quizzes from modules of assigned courses
            module_quizzes = Quiz.objects.filter(
                modules__course_links__course__in=assigned_courses
            ).distinct()

            quizzes = (course_quizzes | module_quizzes).distinct()

            quizzes_data = []
            for quiz in quizzes:
                quizzes_data.append({
                    'id': quiz.id,
                    'title': quiz.title,
                    'time_limit': quiz.time_limit,
                    'passing_score': quiz.passing_score,
                    'total_questions': quiz.total_questions,
                    'total_attempts': quiz.attempts.filter(completed=True).count(),
                    'avg_score': quiz.attempts.filter(completed=True).aggregate(
                        avg=Avg('score')
                    )['avg'] or 0
                })

            return Response(quizzes_data)

        except TeacherProfile.DoesNotExist:
            return Response([])


class TeacherQuizAttemptsView(APIView):
    """List attempts for a quiz"""
    permission_classes = [IsTeacher]

    def get(self, request, quiz_id):
        try:
            profile = request.user.teacher_profile
            from apps.courses.models import Quiz, QuizAttempt

            quiz = Quiz.objects.get(id=quiz_id)

            # Verify access
            assigned_courses = profile.assigned_courses.all()
            has_access = (
                quiz.courses.filter(id__in=assigned_courses).exists() or
                quiz.modules.filter(course_links__course__in=assigned_courses).exists()
            )

            if not has_access:
                return Response(
                    {'error': 'You do not have access to this quiz'},
                    status=status.HTTP_403_FORBIDDEN
                )

            attempts = quiz.attempts.filter(completed=True).select_related('student').order_by('-completed_at')

            attempts_data = []
            for attempt in attempts:
                course = quiz.get_first_course()
                attempts_data.append({
                    'id': attempt.id,
                    'student_id': attempt.student.id,
                    'student_name': attempt.student.name,
                    'student_email': attempt.student.email,
                    'quiz_id': quiz.id,
                    'quiz_title': quiz.title,
                    'course_title': course.title if course else '',
                    'attempt_number': attempt.attempt_number,
                    'score': attempt.score,
                    'total_points': attempt.total_points,
                    'score_percentage': attempt.score_percentage,
                    'is_passed': attempt.is_passed,
                    'time_taken': attempt.time_taken,
                    'completed': attempt.completed,
                    'started_at': attempt.started_at,
                    'completed_at': attempt.completed_at
                })

            return Response(attempts_data)

        except Quiz.DoesNotExist:
            return Response(
                {'error': 'Quiz not found'},
                status=status.HTTP_404_NOT_FOUND
            )


class TeacherQuizAnalyticsView(APIView):
    """Get analytics for a quiz"""
    permission_classes = [IsTeacher]

    def get(self, request, quiz_id):
        try:
            profile = request.user.teacher_profile
            from apps.courses.models import Quiz, QuizAttempt

            quiz = Quiz.objects.get(id=quiz_id)

            # Verify access
            assigned_courses = profile.assigned_courses.all()
            has_access = (
                quiz.courses.filter(id__in=assigned_courses).exists() or
                quiz.modules.filter(course_links__course__in=assigned_courses).exists()
            )

            if not has_access:
                return Response(
                    {'error': 'You do not have access to this quiz'},
                    status=status.HTTP_403_FORBIDDEN
                )

            attempts = quiz.attempts.filter(completed=True)

            total_attempts = attempts.count()
            passed_attempts = attempts.filter(
                score__gte=quiz.passing_score * quiz.total_points / 100
            ).count()

            avg_score = attempts.aggregate(avg=Avg('score'))['avg'] or 0
            avg_time = attempts.aggregate(avg=Avg('time_taken'))['avg'] or 0

            return Response({
                'quiz_id': quiz.id,
                'quiz_title': quiz.title,
                'total_attempts': total_attempts,
                'passed_attempts': passed_attempts,
                'pass_rate': round((passed_attempts / total_attempts * 100) if total_attempts > 0 else 0, 2),
                'average_score': round(avg_score, 2),
                'average_time_seconds': round(avg_time, 0) if avg_time else 0,
                'passing_score': quiz.passing_score
            })

        except Quiz.DoesNotExist:
            return Response(
                {'error': 'Quiz not found'},
                status=status.HTTP_404_NOT_FOUND
            )


# ============== Schedule APIs ==============

class TeacherScheduleListView(APIView):
    """List teacher's schedule"""
    permission_classes = [IsTeacher]

    def get(self, request):
        try:
            profile = request.user.teacher_profile
            schedules = profile.schedules.filter(is_active=True).select_related('course', 'batch')
            serializer = TeacherScheduleSerializer(schedules, many=True)
            return Response(serializer.data)
        except TeacherProfile.DoesNotExist:
            return Response([])


# ============== Announcement APIs ==============

class TeacherAnnouncementListView(APIView):
    """List and create announcements"""
    permission_classes = [IsTeacher]

    def get(self, request):
        try:
            profile = request.user.teacher_profile
            announcements = profile.announcements.select_related('course').order_by('-created_at')
            serializer = TeacherAnnouncementSerializer(announcements, many=True)
            return Response(serializer.data)
        except TeacherProfile.DoesNotExist:
            return Response([])

    def post(self, request):
        try:
            profile = request.user.teacher_profile
            serializer = TeacherAnnouncementCreateSerializer(data=request.data)
            serializer.is_valid(raise_exception=True)

            # Verify course is assigned to teacher
            course = serializer.validated_data.get('course')
            if course and course not in profile.assigned_courses.all():
                return Response(
                    {'error': 'You can only create announcements for your assigned courses'},
                    status=status.HTTP_403_FORBIDDEN
                )

            announcement = serializer.save(teacher=profile)
            return Response(
                TeacherAnnouncementSerializer(announcement).data,
                status=status.HTTP_201_CREATED
            )
        except TeacherProfile.DoesNotExist:
            return Response(
                {'error': 'Teacher profile not found'},
                status=status.HTTP_404_NOT_FOUND
            )


class TeacherAnnouncementDetailView(APIView):
    """Get, update or delete an announcement"""
    permission_classes = [IsTeacher]

    def get_object(self, request, pk):
        profile = request.user.teacher_profile
        return get_object_or_404(TeacherAnnouncement, pk=pk, teacher=profile)

    def get(self, request, pk):
        announcement = self.get_object(request, pk)
        serializer = TeacherAnnouncementSerializer(announcement)
        return Response(serializer.data)

    def put(self, request, pk):
        announcement = self.get_object(request, pk)
        serializer = TeacherAnnouncementCreateSerializer(announcement, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(TeacherAnnouncementSerializer(announcement).data)

    def delete(self, request, pk):
        announcement = self.get_object(request, pk)
        announcement.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


# ============== Admin Teacher Management APIs ==============

class AdminTeacherListView(APIView):
    """List all teachers (Admin only)"""
    permission_classes = [permissions.IsAdminUser]

    def get(self, request):
        teachers = TeacherProfile.objects.select_related('user').prefetch_related('assigned_courses').all()
        serializer = AdminTeacherListSerializer(teachers, many=True)
        return Response(serializer.data)

    def post(self, request):
        """Create a new teacher"""
        serializer = AdminTeacherCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        profile = serializer.save()

        # TODO: Send welcome email with credentials

        return Response(
            AdminTeacherListSerializer(profile).data,
            status=status.HTTP_201_CREATED
        )


class AdminTeacherDetailView(APIView):
    """Get, update or delete a teacher (Admin only)"""
    permission_classes = [permissions.IsAdminUser]

    def get_object(self, pk):
        return get_object_or_404(TeacherProfile, pk=pk)

    def get(self, request, pk):
        profile = self.get_object(pk)
        serializer = AdminTeacherListSerializer(profile)
        return Response(serializer.data)

    def put(self, request, pk):
        profile = self.get_object(pk)
        serializer = AdminTeacherUpdateSerializer(profile, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(AdminTeacherListSerializer(profile).data)

    def delete(self, request, pk):
        profile = self.get_object(pk)
        # Deactivate instead of delete
        user = profile.user
        user.is_active = False
        user.save()
        profile.is_active = False
        profile.save()
        return Response({'message': 'Teacher deactivated successfully'})


class AdminTeacherAssignCoursesView(APIView):
    """Assign courses to a teacher (Admin only)"""
    permission_classes = [permissions.IsAdminUser]

    def post(self, request, pk):
        profile = get_object_or_404(TeacherProfile, pk=pk)
        serializer = AssignCoursesSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        from apps.courses.models import Course
        course_ids = serializer.validated_data['course_ids']
        courses = Course.objects.filter(id__in=course_ids)

        profile.assigned_courses.set(courses)

        return Response({
            'message': 'Courses assigned successfully',
            'assigned_courses': [{'id': c.id, 'title': c.title} for c in profile.assigned_courses.all()]
        })


class AdminTeacherResetPasswordView(APIView):
    """Reset teacher password (Admin only)"""
    permission_classes = [permissions.IsAdminUser]

    def post(self, request, pk):
        profile = get_object_or_404(TeacherProfile, pk=pk)
        user = profile.user

        # Generate temporary password
        import secrets
        import string
        temp_password = ''.join(secrets.choice(string.ascii_letters + string.digits) for _ in range(12))

        user.set_password(temp_password)
        user.save()

        profile.must_change_password = True
        profile.save()

        # TODO: Send email with new password

        return Response({
            'message': 'Password reset successfully',
            'temporary_password': temp_password  # In production, send via email only
        })
