from rest_framework import generics, permissions, status, filters
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.views import APIView
from django_filters.rest_framework import DjangoFilterBackend
from drf_spectacular.utils import extend_schema, extend_schema_view, OpenApiExample, OpenApiParameter
from drf_spectacular.openapi import OpenApiResponse
from django.db.models import Q, Case, When

from .models import (
    Category, Course, Module, VideoLesson, StudentProgress,
    Assignment, Quiz, QuizQuestion, QuizChoice, AssignmentSubmission,
    QuizAttempt, QuizAnswer, ModuleProgress, Certificate,
    DailyStreak, DailyActivity
)
from .serializers import (
    CategorySerializer, CourseListSerializer, CourseDetailSerializer,
    ModuleSerializer, VideoLessonSerializer, StudentProgressSerializer,
    AssignmentSerializer, AssignmentSubmissionSerializer, QuizSerializer,
    QuizAttemptSerializer, QuizAnswerSerializer, ModuleProgressSerializer,
    CertificateListSerializer, CertificateDetailSerializer, CertificateVerificationSerializer,
    DailyStreakSerializer, DailyActivitySerializer, RecordActivitySerializer, StreakResponseSerializer
)

@extend_schema_view(
    get=extend_schema(
        summary="List all categories",
        description="Get all available course categories with course counts",
        responses={200: CategorySerializer(many=True)},
        tags=['Student - Courses']
    )
)
class CategoryListView(generics.ListAPIView):
    """
    List all available course categories for students.
    """
    queryset = Category.objects.all().order_by('name')
    serializer_class = CategorySerializer
    permission_classes = [permissions.AllowAny]

@extend_schema_view(
    get=extend_schema(
        summary="List courses",
        description="Get list of published courses with filtering and search",
        parameters=[
            OpenApiParameter(
                name='category',
                description='Filter by category ID',
                required=False,
                type=int
            ),
            OpenApiParameter(
                name='is_free',
                description='Filter by free courses (true/false)',
                required=False,
                type=bool
            ),
            OpenApiParameter(
                name='search',
                description='Search in course title and description',
                required=False,
                type=str
            ),
        ],
        responses={200: CourseListSerializer(many=True)},
        examples=[
            OpenApiExample(
                'Course List Response',
                value=[
                    {
                        "id": 1,
                        "title": "Complete Python Web Development",
                        "description": "Learn Python Django framework from scratch",
                        "category_name": "Web Development",
                        "price": "4999.00",
                        "price_display": "₹4999",
                        "total_price_display": "₹5899",
                        "thumbnail": "/media/course_thumbnails/python_course.jpg",
                        "thumbnail_url": "https://yoursite.com/media/course_thumbnails/python_course.jpg",
                        "preview_video": "https://www.youtube.com/watch?v=abc123",
                        "preview_video_url": "https://www.youtube.com/watch?v=abc123",
                        "is_free_course": False,
                        "is_enrolled": False,
                        "module_count": 5,
                        "total_lessons": 25,
                        "allow_public_enrollment": True
                    }
                ]
            )
        ],
        tags=['Student - Courses']
    )
)
class CourseListView(generics.ListAPIView):
    """
    List all published courses available to students.
    Supports filtering by category, free status, enrollment type, and text search.
    Includes all published courses (online_purchase, admin_only, enquiry_only).
    """
    serializer_class = CourseListSerializer
    permission_classes = [permissions.AllowAny]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter]
    filterset_fields = ['category', 'is_free', 'enrollment_type']
    search_fields = ['title', 'description', 'curriculum', 'what_you_will_learn']

    def get_queryset(self):
        # Show all published courses (including admin_only and enquiry_only)
        return Course.objects.filter(is_published=True).select_related('category')

@extend_schema_view(
    get=extend_schema(
        summary="Get course details",
        description="Get detailed information about a specific course including modules and lessons",
        responses={
            200: CourseDetailSerializer,
            404: OpenApiResponse(description="Course not found")
        },
        examples=[
            OpenApiExample(
                'Course Detail Response',
                value={
                    "id": 1,
                    "title": "Complete Python Web Development",
                    "description": "Learn Python Django framework from scratch",
                    "category": {
                        "id": 1,
                        "name": "Web Development",
                        "description": "Learn modern web development technologies"
                    },
                    "price_display": "₹4999",
                    "total_price_display": "₹5899",
                    "thumbnail": "/media/course_thumbnails/python_course.jpg",
                    "thumbnail_url": "https://yoursite.com/media/course_thumbnails/python_course.jpg",
                    "preview_video": "https://www.youtube.com/watch?v=abc123",
                    "preview_video_url": "https://www.youtube.com/watch?v=abc123",
                    "is_enrolled": False,
                    "allow_public_enrollment": True,
                    "modules": [
                        {
                            "id": 1,
                            "title": "Introduction to Python",
                            "order": 1,
                            "lesson_count": 5,
                            "video_lessons": []
                        }
                    ]
                }
            )
        ],
        tags=['Student - Courses']
    )
)
class CourseDetailView(generics.RetrieveAPIView):
    """
    Get detailed information about a specific course.
    Shows all published courses (including admin_only and enquiry_only).
    The response includes flags like `is_admin_only`, `can_purchase_online`
    so the app can decide how to handle enrollment.
    """
    serializer_class = CourseDetailSerializer
    permission_classes = [permissions.AllowAny]

    def get_queryset(self):
        # Show all published courses (including admin_only and enquiry_only)
        # The serializer response includes `is_admin_only`, `can_purchase_online`,
        # `is_enquiry_only` flags for the app to determine enrollment options
        return Course.objects.filter(is_published=True).select_related('category', 'created_by')

@extend_schema_view(
    get=extend_schema(
        summary="List enrolled courses",
        description="Get list of courses the authenticated student is enrolled in",
        responses={
            200: CourseListSerializer(many=True),
            401: OpenApiResponse(description="Authentication required")
        },
        tags=['Student - Enrollments']
    )
)
class EnrolledCoursesView(generics.ListAPIView):
    """
    List courses that the authenticated student is enrolled in with full details.
    Includes modules, course-level assignments, quizzes, and PDFs.
    """
    serializer_class = CourseDetailSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        from apps.payments.models import Enrollment
        enrolled_course_ids = Enrollment.objects.filter(
            user=self.request.user,
            active=True
        ).values_list('course_id', flat=True)

        return Course.objects.filter(
            id__in=enrolled_course_ids
        ).select_related('category').prefetch_related(
            'module_links__module',
            'assignment_links__assignment',
            'quiz_links__quiz',
            'pdf_links__pdf_note'
        )

@extend_schema_view(
    get=extend_schema(
        summary="Get student progress",
        description="Get progress for all courses or a specific course",
        parameters=[
            OpenApiParameter(
                name='course_id',
                description='Filter progress by specific course ID',
                required=False,
                type=int
            ),
        ],
        responses={
            200: StudentProgressSerializer(many=True),
            401: OpenApiResponse(description="Authentication required")
        },
        tags=['Student - Progress']
    ),
    post=extend_schema(
        summary="Update video progress",
        description="Update student's progress for a specific video lesson",
        request=StudentProgressSerializer,
        responses={
            200: StudentProgressSerializer,
            400: OpenApiResponse(description="Invalid data")
        },
        examples=[
            OpenApiExample(
                'Update Progress Request',
                value={
                    "video_lesson_id": 1,
                    "course_id": 1,
                    "completed_percentage": 75.5,
                    "completed": False
                }
            )
        ],
        tags=['Student - Progress']
    )
)
class StudentProgressView(APIView):
    """
    View and update student progress for video lessons.
    """
    permission_classes = [permissions.IsAuthenticated]
    
    def get(self, request):
        course_id = request.query_params.get('course_id')
        queryset = StudentProgress.objects.filter(user=request.user)
        
        if course_id:
            queryset = queryset.filter(course_id=course_id)
        
        queryset = queryset.select_related('course', 'video_lesson').order_by('-last_watched_at')
        serializer = StudentProgressSerializer(queryset, many=True)
        return Response(serializer.data)
    
    def post(self, request):
        # Update progress for a specific video
        video_lesson_id = request.data.get('video_lesson_id')
        course_id = request.data.get('course_id')
        completed_percentage = request.data.get('completed_percentage', 0)
        completed = request.data.get('completed', False)
        watch_time_minutes = request.data.get('watch_time_minutes', 0)  # Optional: track watch time

        if not video_lesson_id or not course_id:
            return Response({
                'error': 'video_lesson_id and course_id are required'
            }, status=status.HTTP_400_BAD_REQUEST)

        # Check if user is enrolled in the course
        from apps.payments.models import Enrollment
        if not Enrollment.objects.filter(user=request.user, course_id=course_id, active=True).exists():
            return Response({
                'error': 'You are not enrolled in this course'
            }, status=status.HTTP_403_FORBIDDEN)

        # Check if this is a new completion (for streak tracking)
        was_completed_before = StudentProgress.objects.filter(
            user=request.user,
            video_lesson_id=video_lesson_id,
            completed=True
        ).exists()

        # Update or create progress
        progress, created = StudentProgress.objects.update_or_create(
            user=request.user,
            course_id=course_id,
            video_lesson_id=video_lesson_id,
            defaults={
                'completed_percentage': completed_percentage,
                'completed': completed
            }
        )

        # Record activity for streak (only if newly completed or significant progress)
        if completed and not was_completed_before:
            # New video completion - record activity
            DailyActivity.record_activity(request.user, 'video', watch_time_minutes)
        elif completed_percentage > 0 and watch_time_minutes > 0:
            # Just watching - update learning time but don't count as video completion
            DailyActivity.record_activity(request.user, 'general', watch_time_minutes)

        # Get updated streak info
        streak = DailyStreak.get_or_create_for_user(request.user)

        serializer = StudentProgressSerializer(progress)
        response_data = serializer.data
        response_data['streak'] = {
            'current_streak': streak.current_streak,
            'longest_streak': streak.longest_streak,
            'is_active_today': streak.last_activity_date == DailyStreak._meta.model.objects.filter(
                student=request.user
            ).first().last_activity_date if streak.last_activity_date else False
        }

        return Response(response_data)

@extend_schema(
    summary="Search courses",
    description="Search courses by title, description, or category",
    parameters=[
        OpenApiParameter(
            name='q',
            description='Search query',
            required=True,
            type=str
        ),
    ],
    responses={200: CourseListSerializer(many=True)},
    tags=['Student - Courses']
)
@api_view(['GET'])
@permission_classes([permissions.AllowAny])
def search_courses(request):
    """
    Search for courses across title, description, and category.
    """
    query = request.query_params.get('q', '')
    if not query:
        return Response({'error': 'Search query is required'}, status=400)
    
    courses = Course.objects.filter(
        Q(title__icontains=query) | 
        Q(description__icontains=query) |
        Q(curriculum__icontains=query) |
        Q(what_you_will_learn__icontains=query) |
        Q(category__name__icontains=query),
        is_published=True,
        allow_public_enrollment=True
    ).select_related('category').distinct()
    
    serializer = CourseListSerializer(courses, many=True, context={'request': request})
    return Response(serializer.data)


# Assignment and Quiz API Views

@extend_schema_view(
    get=extend_schema(
        summary="Get module assignments",
        description="Get all assignments for a specific module",
        responses={200: AssignmentSerializer(many=True)},
        tags=['Student - Assignments']
    )
)
class ModuleAssignmentsView(generics.ListAPIView):
    """
    List assignments for a specific module.
    """
    serializer_class = AssignmentSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        module_id = self.kwargs['module_id']
        # Check if user is enrolled in the course
        from apps.payments.models import Enrollment
        module = Module.objects.get(id=module_id)

        if not Enrollment.objects.filter(
            user=self.request.user,
            course=module.course,
            active=True
        ).exists():
            return Assignment.objects.none()

        # Get assignments linked to this module via many-to-many relationship
        assignment_links = module.assignment_links.select_related('assignment').order_by('order')
        assignment_ids = [link.assignment_id for link in assignment_links]

        # Return assignments preserving the order from the through model
        preserved = Case(*[When(pk=pk, then=pos) for pos, pk in enumerate(assignment_ids)])
        return Assignment.objects.filter(id__in=assignment_ids).order_by(preserved)


@extend_schema_view(
    get=extend_schema(
        summary="Get assignment details",
        description="Get detailed information about a specific assignment",
        responses={200: AssignmentSerializer},
        tags=['Student - Assignments']
    )
)
class AssignmentDetailView(generics.RetrieveAPIView):
    """
    Get detailed information about a specific assignment.
    """
    serializer_class = AssignmentSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        # Check if user is enrolled in any course that contains this assignment
        from apps.payments.models import Enrollment

        # Get enrolled courses for the user
        enrolled_course_ids = Enrollment.objects.filter(
            user=self.request.user,
            active=True
        ).values_list('course_id', flat=True)

        # Return assignments that are linked to modules in enrolled courses
        return Assignment.objects.filter(
            Q(modules__course_id__in=enrolled_course_ids) |
            Q(courses__id__in=enrolled_course_ids) |
            Q(video_lessons__module__course_id__in=enrolled_course_ids)
        ).distinct()


@extend_schema_view(
    get=extend_schema(
        summary="Get user's assignment submissions",
        description="Get all assignment submissions for the authenticated user",
        responses={200: AssignmentSubmissionSerializer(many=True)},
        tags=['Student - Assignments']
    ),
    post=extend_schema(
        summary="Create assignment submission",
        description="Submit an assignment with GitHub URL",
        request=AssignmentSubmissionSerializer,
        responses={201: AssignmentSubmissionSerializer},
        tags=['Student - Assignments']
    )
)
class AssignmentSubmissionView(generics.ListCreateAPIView):
    """
    List user's assignment submissions and create new submissions.
    """
    serializer_class = AssignmentSubmissionSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        return AssignmentSubmission.objects.filter(
            student=self.request.user
        ).select_related('assignment').prefetch_related('assignment__courses', 'assignment__modules', 'assignment__video_lessons')

    def perform_create(self, serializer):
        assignment = serializer.validated_data['assignment']

        # Check if user is enrolled in any course that contains this assignment
        from apps.payments.models import Enrollment

        # Get all courses that contain this assignment (at any level)
        course_ids = set()
        course_ids.update(assignment.courses.values_list('id', flat=True))
        course_ids.update(assignment.modules.values_list('course_id', flat=True))
        course_ids.update(assignment.video_lessons.values_list('module__course_id', flat=True))

        if not course_ids or not Enrollment.objects.filter(
            user=self.request.user,
            course_id__in=course_ids,
            active=True
        ).exists():
            from rest_framework.exceptions import PermissionDenied
            raise PermissionDenied("You are not enrolled in this course")
        
        # Check if submission already exists
        if AssignmentSubmission.objects.filter(
            assignment=assignment,
            student=self.request.user
        ).exists():
            from rest_framework.exceptions import ValidationError
            raise ValidationError("Assignment already submitted")
        
        serializer.save(student=self.request.user)


@extend_schema_view(
    get=extend_schema(
        summary="Get assignment submission details",
        description="Get details of a specific assignment submission",
        responses={200: AssignmentSubmissionSerializer},
        tags=['Student - Assignments']
    ),
    put=extend_schema(
        summary="Update assignment submission",
        description="Update assignment submission (only if in draft status)",
        request=AssignmentSubmissionSerializer,
        responses={200: AssignmentSubmissionSerializer},
        tags=['Student - Assignments']
    ),
    patch=extend_schema(
        summary="Submit assignment",
        description="Submit a draft assignment for review",
        responses={200: AssignmentSubmissionSerializer},
        tags=['Student - Assignments']
    )
)
class AssignmentSubmissionDetailView(generics.RetrieveUpdateAPIView):
    """
    Get, update, and submit assignment submissions.
    """
    serializer_class = AssignmentSubmissionSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        return AssignmentSubmission.objects.filter(student=self.request.user)
    
    def patch(self, request, *args, **kwargs):
        """Submit the assignment"""
        submission = self.get_object()
        if submission.status != 'draft':
            return Response(
                {'error': 'Assignment already submitted'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        submission.submit()
        serializer = self.get_serializer(submission)
        return Response(serializer.data)


@extend_schema_view(
    get=extend_schema(
        summary="Get module quizzes",
        description="Get all quizzes for a specific module",
        responses={200: QuizSerializer(many=True)},
        tags=['Student - Quizzes']
    )
)
class ModuleQuizzesView(generics.ListAPIView):
    """
    List quizzes for a specific module.
    """
    serializer_class = QuizSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        module_id = self.kwargs['module_id']
        # Check if user is enrolled in the course
        from apps.payments.models import Enrollment
        module = Module.objects.get(id=module_id)

        if not Enrollment.objects.filter(
            user=self.request.user,
            course=module.course,
            active=True
        ).exists():
            return Quiz.objects.none()

        # Get quizzes linked to this module via many-to-many relationship
        quiz_links = module.quiz_links.select_related('quiz').order_by('order')
        quiz_ids = [link.quiz_id for link in quiz_links]

        # Return quizzes preserving the order from the through model
        preserved = Case(*[When(pk=pk, then=pos) for pos, pk in enumerate(quiz_ids)])
        return Quiz.objects.filter(id__in=quiz_ids).order_by(preserved).prefetch_related('questions__choices')


@extend_schema_view(
    get=extend_schema(
        summary="Get quiz details",
        description="Get detailed information about a specific quiz",
        responses={200: QuizSerializer},
        tags=['Student - Quizzes']
    )
)
class QuizDetailView(generics.RetrieveAPIView):
    """
    Get detailed information about a specific quiz.
    """
    serializer_class = QuizSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        # Check if user is enrolled in any course that contains this quiz
        from apps.payments.models import Enrollment

        # Get enrolled courses for the user
        enrolled_course_ids = Enrollment.objects.filter(
            user=self.request.user,
            active=True
        ).values_list('course_id', flat=True)

        # Return quizzes that are linked to modules/courses/videos in enrolled courses
        return Quiz.objects.filter(
            Q(modules__course_id__in=enrolled_course_ids) |
            Q(courses__id__in=enrolled_course_ids) |
            Q(video_lessons__module__course_id__in=enrolled_course_ids)
        ).distinct().prefetch_related('questions__choices')


@extend_schema_view(
    post=extend_schema(
        summary="Start quiz attempt",
        description="Start a new quiz attempt",
        responses={201: QuizAttemptSerializer},
        tags=['Student - Quizzes']
    )
)
class StartQuizAttemptView(generics.CreateAPIView):
    """
    Start a new quiz attempt.
    """
    serializer_class = QuizAttemptSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def create(self, request, *args, **kwargs):
        quiz_id = kwargs['quiz_id']
        quiz = Quiz.objects.get(id=quiz_id)

        # Check if user is enrolled in any course that contains this quiz
        from apps.payments.models import Enrollment

        # Get all courses that contain this quiz (at any level)
        course_ids = set()
        course_ids.update(quiz.courses.values_list('id', flat=True))
        course_ids.update(quiz.modules.values_list('course_id', flat=True))
        course_ids.update(quiz.video_lessons.values_list('module__course_id', flat=True))

        if not course_ids or not Enrollment.objects.filter(
            user=request.user,
            course_id__in=course_ids,
            active=True
        ).exists():
            return Response(
                {'error': 'You are not enrolled in this course'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        # Count all previous attempts (completed and incomplete) for attempt numbering
        user_attempts = QuizAttempt.objects.filter(
            quiz=quiz,
            student=request.user
        ).count()
        
        # Create new attempt (no limit restrictions)
        attempt = QuizAttempt.objects.create(
            quiz=quiz,
            student=request.user,
            attempt_number=user_attempts + 1,
            total_points=quiz.total_points
        )
        
        serializer = self.get_serializer(attempt)
        return Response(serializer.data, status=status.HTTP_201_CREATED)


@extend_schema_view(
    post=extend_schema(
        summary="Submit quiz answers",
        description="Submit answers for a quiz attempt",
        request=QuizAnswerSerializer(many=True),
        responses={200: QuizAttemptSerializer},
        tags=['Student - Quizzes']
    )
)
class SubmitQuizAnswersView(APIView):
    """
    Submit answers for a quiz attempt.
    """
    permission_classes = [permissions.IsAuthenticated]
    
    def post(self, request, attempt_id):
        try:
            attempt = QuizAttempt.objects.get(
                id=attempt_id,
                student=request.user,
                completed=False
            )
        except QuizAttempt.DoesNotExist:
            return Response(
                {'error': 'Quiz attempt not found or already completed'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        answers_data = request.data.get('answers', [])
        total_score = 0
        
        for answer_data in answers_data:
            question_id = answer_data.get('question')
            selected_choice_id = answer_data.get('selected_choice')
            text_answer = answer_data.get('text_answer', '')
            
            try:
                question = QuizQuestion.objects.get(id=question_id, quiz=attempt.quiz)
            except QuizQuestion.DoesNotExist:
                continue
            
            points_earned = 0
            is_correct = False
            
            if question.question_type == 'multiple_choice':
                try:
                    selected_choice = QuizChoice.objects.get(id=selected_choice_id)
                    is_correct = selected_choice.is_correct
                    if is_correct:
                        points_earned = question.points
                except QuizChoice.DoesNotExist:
                    pass
            elif question.question_type == 'true_false':
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
                text_answer=text_answer,
                is_correct=is_correct,
                points_earned=points_earned
            )
            
            total_score += points_earned
        
        # Update attempt
        attempt.score = total_score
        attempt.complete()

        # Update module progress for all modules that contain this quiz
        quiz_modules = attempt.quiz.modules.all()
        for module in quiz_modules:
            try:
                module_progress = ModuleProgress.objects.get(
                    student=request.user,
                    module=module
                )
                module_progress.check_completion()
            except ModuleProgress.DoesNotExist:
                pass
        
        serializer = QuizAttemptSerializer(attempt)
        return Response(serializer.data)


@extend_schema_view(
    get=extend_schema(
        summary="Get user's quiz attempts",
        description="Get all quiz attempts for the authenticated user",
        responses={200: QuizAttemptSerializer(many=True)},
        tags=['Student - Quizzes']
    )
)
class UserQuizAttemptsView(generics.ListAPIView):
    """
    List user's quiz attempts.
    """
    serializer_class = QuizAttemptSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        return QuizAttempt.objects.filter(
            student=self.request.user
        ).select_related('quiz', 'quiz__module', 'quiz__module__course').order_by('-started_at')


@extend_schema_view(
    get=extend_schema(
        summary="Get module progress",
        description="Get progress for all modules or a specific course",
        parameters=[
            OpenApiParameter(
                name='course_id',
                description='Filter progress by specific course ID',
                required=False,
                type=int
            ),
        ],
        responses={200: ModuleProgressSerializer(many=True)},
        tags=['Student - Progress']
    )
)
class ModuleProgressView(generics.ListAPIView):
    """
    Get module progress for the authenticated user.
    """
    serializer_class = ModuleProgressSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        queryset = ModuleProgress.objects.filter(student=self.request.user)
        course_id = self.request.query_params.get('course_id')

        if course_id:
            queryset = queryset.filter(module__course_id=course_id)

        return queryset.select_related('module', 'module__course').order_by('module__order')


# ==================== CERTIFICATE VIEWS ====================

@extend_schema_view(
    get=extend_schema(
        summary="List My Certificates",
        description="Get all certificates earned by the authenticated user",
        responses={200: CertificateListSerializer(many=True)},
        tags=['Student - Certificates']
    )
)
class CertificateListView(generics.ListAPIView):
    """
    List all certificates earned by the authenticated user.
    """
    serializer_class = CertificateListSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ['certificate_type', 'is_revoked']
    ordering = ['-issue_date']

    def get_queryset(self):
        return Certificate.objects.filter(
            student=self.request.user,
            is_revoked=False
        ).select_related('course', 'student')


@extend_schema_view(
    get=extend_schema(
        summary="Get Certificate Details",
        description="Get detailed information about a specific certificate",
        responses={
            200: CertificateDetailSerializer,
            404: OpenApiResponse(description="Certificate not found")
        },
        tags=['Student - Certificates']
    )
)
class CertificateDetailView(generics.RetrieveAPIView):
    """
    Get detailed information about a specific certificate.
    """
    serializer_class = CertificateDetailSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return Certificate.objects.filter(
            student=self.request.user
        ).select_related('course', 'student', 'enrollment')


@extend_schema_view(
    get=extend_schema(
        summary="Verify Certificate",
        description="Verify a certificate using its verification code. This endpoint is public.",
        parameters=[
            OpenApiParameter(
                name='code',
                description='Certificate verification code',
                required=True,
                type=str
            ),
        ],
        responses={
            200: CertificateVerificationSerializer,
            404: OpenApiResponse(description="Certificate not found")
        },
        tags=['Public - Certificate Verification']
    )
)
class CertificateVerifyView(APIView):
    """
    Verify a certificate using its verification code.
    This endpoint is public and does not require authentication.
    """
    permission_classes = [permissions.AllowAny]

    def get(self, request):
        code = request.query_params.get('code', '').strip()

        if not code:
            return Response({
                'is_valid': False,
                'status': 'error',
                'message': 'Verification code is required.'
            }, status=status.HTTP_400_BAD_REQUEST)

        try:
            certificate = Certificate.objects.select_related(
                'student', 'course'
            ).get(verification_code=code)

            if certificate.is_revoked:
                return Response({
                    'is_valid': False,
                    'status': 'revoked',
                    'message': f'This certificate has been revoked. Reason: {certificate.revoked_reason or "Not specified"}',
                    'certificate_number': certificate.certificate_number,
                })

            return Response({
                'is_valid': True,
                'status': 'valid',
                'message': 'This certificate is valid and verified.',
                'certificate_number': certificate.certificate_number,
                'student_name': certificate.student.name,
                'course_title': certificate.course.title,
                'completion_date': certificate.completion_date,
                'issue_date': certificate.issue_date,
                'certificate_type': certificate.get_certificate_type_display(),
                'grade': certificate.grade,
                'signed_by': certificate.signed_by,
                'signed_by_title': certificate.signed_by_title,
            })

        except Certificate.DoesNotExist:
            return Response({
                'is_valid': False,
                'status': 'not_found',
                'message': 'No certificate found with this verification code.'
            }, status=status.HTTP_404_NOT_FOUND)


@extend_schema_view(
    get=extend_schema(
        summary="Download Certificate PDF",
        description="Download the PDF file of a certificate",
        responses={
            200: OpenApiResponse(description="PDF file"),
            404: OpenApiResponse(description="Certificate not found or PDF not available")
        },
        tags=['Student - Certificates']
    )
)
class CertificateDownloadView(APIView):
    """
    Download certificate PDF file.
    """
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, pk):
        try:
            certificate = Certificate.objects.get(
                pk=pk,
                student=request.user
            )

            # Generate PDF if it doesn't exist
            if not certificate.pdf_file:
                try:
                    from apps.courses.certificate_generator import generate_certificate_pdf
                    from django.core.files.base import ContentFile

                    pdf_buffer = generate_certificate_pdf(certificate)
                    pdf_filename = f"certificate_{certificate.certificate_number}.pdf"
                    certificate.pdf_file.save(pdf_filename, ContentFile(pdf_buffer.getvalue()), save=True)
                except Exception as e:
                    return Response({
                        'error': f'Failed to generate PDF: {str(e)}'
                    }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

            from django.http import FileResponse
            return FileResponse(
                certificate.pdf_file.open('rb'),
                as_attachment=True,
                filename=f'certificate_{certificate.certificate_number}.pdf'
            )

        except Certificate.DoesNotExist:
            return Response({
                'error': 'Certificate not found.'
            }, status=status.HTTP_404_NOT_FOUND)


# ==================== STREAK VIEWS ====================

@extend_schema_view(
    get=extend_schema(
        summary="Get My Streak",
        description="Get the current user's streak information including current streak, longest streak, and activity status",
        responses={200: DailyStreakSerializer},
        tags=['Student - Streaks']
    )
)
class StreakView(APIView):
    """
    Get current user's streak information.
    This also checks and updates streak status (e.g., if streak is broken).
    """
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        streak = DailyStreak.get_or_create_for_user(request.user)
        serializer = DailyStreakSerializer(streak)
        return Response(serializer.data)


@extend_schema(
    summary="Record Activity",
    description="Record a learning activity to update the streak. Call this when user watches a video, takes a quiz, or submits an assignment.",
    request=RecordActivitySerializer,
    responses={
        200: StreakResponseSerializer,
        400: OpenApiResponse(description="Invalid request")
    },
    tags=['Student - Streaks']
)
@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def record_activity(request):
    """
    Record a learning activity and update the streak.
    """
    serializer = RecordActivitySerializer(data=request.data)
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    activity_type = serializer.validated_data.get('activity_type', 'general')
    minutes = serializer.validated_data.get('minutes', 0)

    # Record the activity
    DailyActivity.record_activity(request.user, activity_type, minutes)

    # Get updated streak
    streak = DailyStreak.get_or_create_for_user(request.user)

    from django.utils import timezone
    from datetime import timedelta
    today = timezone.now().date()

    # Calculate streak status
    if streak.last_activity_date == today:
        streak_status = 'active'
    elif streak.last_activity_date == today - timedelta(days=1):
        streak_status = 'at_risk'
    else:
        streak_status = 'broken'

    return Response({
        'success': True,
        'message': f'Activity recorded! Your streak is now {streak.current_streak} days.',
        'current_streak': streak.current_streak,
        'longest_streak': streak.longest_streak,
        'total_active_days': streak.total_active_days,
        'is_active_today': streak.last_activity_date == today,
        'streak_status': streak_status
    })


@extend_schema_view(
    get=extend_schema(
        summary="Get Activity History",
        description="Get daily activity history for the current user. Supports filtering by date range.",
        parameters=[
            OpenApiParameter(
                name='days',
                description='Number of days to look back (default: 30, max: 365)',
                required=False,
                type=int
            ),
            OpenApiParameter(
                name='start_date',
                description='Start date for range filter (YYYY-MM-DD)',
                required=False,
                type=str
            ),
            OpenApiParameter(
                name='end_date',
                description='End date for range filter (YYYY-MM-DD)',
                required=False,
                type=str
            ),
        ],
        responses={200: DailyActivitySerializer(many=True)},
        tags=['Student - Streaks']
    )
)
class ActivityHistoryView(generics.ListAPIView):
    """
    Get daily activity history for the authenticated user.
    """
    serializer_class = DailyActivitySerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        from django.utils import timezone
        from datetime import timedelta

        queryset = DailyActivity.objects.filter(student=self.request.user)

        # Filter by days back
        days = self.request.query_params.get('days')
        if days:
            try:
                days = min(int(days), 365)  # Max 365 days
                start_date = timezone.now().date() - timedelta(days=days)
                queryset = queryset.filter(activity_date__gte=start_date)
            except ValueError:
                pass

        # Filter by date range
        start_date = self.request.query_params.get('start_date')
        end_date = self.request.query_params.get('end_date')

        if start_date:
            queryset = queryset.filter(activity_date__gte=start_date)
        if end_date:
            queryset = queryset.filter(activity_date__lte=end_date)

        return queryset.order_by('-activity_date')


@extend_schema(
    summary="Get Weekly Activity Summary",
    description="Get a summary of activity for the last 7 days including days with activity",
    responses={
        200: OpenApiResponse(
            description="Weekly activity summary",
            response={
                'type': 'object',
                'properties': {
                    'week_start': {'type': 'string', 'format': 'date'},
                    'week_end': {'type': 'string', 'format': 'date'},
                    'total_activities': {'type': 'integer'},
                    'total_videos': {'type': 'integer'},
                    'total_quizzes': {'type': 'integer'},
                    'total_assignments': {'type': 'integer'},
                    'total_learning_minutes': {'type': 'integer'},
                    'active_days': {'type': 'integer'},
                    'daily_breakdown': {'type': 'array'}
                }
            }
        )
    },
    tags=['Student - Streaks']
)
@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def weekly_summary(request):
    """
    Get weekly activity summary.
    """
    from django.utils import timezone
    from datetime import timedelta

    today = timezone.now().date()
    week_start = today - timedelta(days=6)

    activities = DailyActivity.objects.filter(
        student=request.user,
        activity_date__gte=week_start,
        activity_date__lte=today
    ).order_by('activity_date')

    # Build daily breakdown
    daily_breakdown = []
    activity_dict = {a.activity_date: a for a in activities}

    total_activities = 0
    total_videos = 0
    total_quizzes = 0
    total_assignments = 0
    total_minutes = 0
    active_days = 0

    for i in range(7):
        date = week_start + timedelta(days=i)
        activity = activity_dict.get(date)

        if activity:
            daily_breakdown.append({
                'date': date,
                'activities_count': activity.activities_count,
                'videos_watched': activity.videos_watched,
                'quizzes_attempted': activity.quizzes_attempted,
                'assignments_submitted': activity.assignments_submitted,
                'learning_minutes': activity.learning_minutes,
                'has_activity': True
            })
            total_activities += activity.activities_count
            total_videos += activity.videos_watched
            total_quizzes += activity.quizzes_attempted
            total_assignments += activity.assignments_submitted
            total_minutes += activity.learning_minutes
            active_days += 1
        else:
            daily_breakdown.append({
                'date': date,
                'activities_count': 0,
                'videos_watched': 0,
                'quizzes_attempted': 0,
                'assignments_submitted': 0,
                'learning_minutes': 0,
                'has_activity': False
            })

    return Response({
        'week_start': week_start,
        'week_end': today,
        'total_activities': total_activities,
        'total_videos': total_videos,
        'total_quizzes': total_quizzes,
        'total_assignments': total_assignments,
        'total_learning_minutes': total_minutes,
        'active_days': active_days,
        'daily_breakdown': daily_breakdown
    })
