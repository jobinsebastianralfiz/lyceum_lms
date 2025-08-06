from rest_framework import generics, permissions, status, filters
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.views import APIView
from django_filters.rest_framework import DjangoFilterBackend
from drf_spectacular.utils import extend_schema, extend_schema_view, OpenApiExample, OpenApiParameter
from drf_spectacular.openapi import OpenApiResponse
from django.db.models import Q

from .models import (
    Category, Course, Module, VideoLesson, StudentProgress,
    Assignment, Quiz, QuizQuestion, QuizChoice, AssignmentSubmission,
    QuizAttempt, QuizAnswer, ModuleProgress
)
from .serializers import (
    CategorySerializer, CourseListSerializer, CourseDetailSerializer,
    ModuleSerializer, VideoLessonSerializer, StudentProgressSerializer,
    AssignmentSerializer, AssignmentSubmissionSerializer, QuizSerializer,
    QuizAttemptSerializer, QuizAnswerSerializer, ModuleProgressSerializer
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
                        "is_free_course": False,
                        "is_enrolled": False,
                        "module_count": 5,
                        "total_lessons": 25
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
    Supports filtering by category, free status, and text search.
    """
    serializer_class = CourseListSerializer
    permission_classes = [permissions.AllowAny]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter]
    filterset_fields = ['category', 'is_free']
    search_fields = ['title', 'description']
    
    def get_queryset(self):
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
                    "is_enrolled": False,
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
    """
    queryset = Course.objects.filter(is_published=True).select_related('category').prefetch_related('modules__video_lessons')
    serializer_class = CourseDetailSerializer
    permission_classes = [permissions.AllowAny]

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
    List courses that the authenticated student is enrolled in.
    """
    serializer_class = CourseListSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        from apps.payments.models import Enrollment
        enrolled_course_ids = Enrollment.objects.filter(
            user=self.request.user,
            active=True
        ).values_list('course_id', flat=True)
        
        return Course.objects.filter(
            id__in=enrolled_course_ids
        ).select_related('category')

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
        
        serializer = StudentProgressSerializer(progress)
        return Response(serializer.data)

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
        Q(category__name__icontains=query),
        is_published=True
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
        
        return Assignment.objects.filter(module_id=module_id).order_by('order')


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
        # Check if user is enrolled in the course
        from apps.payments.models import Enrollment
        return Assignment.objects.filter(
            module__course__enrollment__user=self.request.user,
            module__course__enrollment__active=True
        )


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
        ).select_related('assignment', 'assignment__module', 'assignment__module__course')
    
    def perform_create(self, serializer):
        assignment = serializer.validated_data['assignment']
        
        # Check if user is enrolled in the course
        from apps.payments.models import Enrollment
        if not Enrollment.objects.filter(
            user=self.request.user,
            course=assignment.module.course,
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
        
        return Quiz.objects.filter(module_id=module_id).order_by('order').prefetch_related('questions__choices')


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
        # Check if user is enrolled in the course
        from apps.payments.models import Enrollment
        return Quiz.objects.filter(
            module__course__enrollment__user=self.request.user,
            module__course__enrollment__active=True
        ).prefetch_related('questions__choices')


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
        
        # Check if user is enrolled
        from apps.payments.models import Enrollment
        if not Enrollment.objects.filter(
            user=request.user,
            course=quiz.module.course,
            active=True
        ).exists():
            return Response(
                {'error': 'You are not enrolled in this course'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        # Check attempt limit
        user_attempts = QuizAttempt.objects.filter(
            quiz=quiz,
            student=request.user,
            completed=True
        ).count()
        
        if user_attempts >= quiz.max_attempts:
            return Response(
                {'error': 'Maximum attempts reached'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Create new attempt
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
        
        # Update module progress
        try:
            module_progress = ModuleProgress.objects.get(
                student=request.user,
                module=attempt.quiz.module
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
