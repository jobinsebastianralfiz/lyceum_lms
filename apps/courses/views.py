from rest_framework import generics, permissions, status, filters
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.views import APIView
from django_filters.rest_framework import DjangoFilterBackend
from drf_spectacular.utils import extend_schema, extend_schema_view, OpenApiExample, OpenApiParameter
from drf_spectacular.openapi import OpenApiResponse
from django.db.models import Q

from .models import Category, Course, Module, VideoLesson, StudentProgress
from .serializers import (
    CategorySerializer, CourseListSerializer, CourseDetailSerializer,
    ModuleSerializer, VideoLessonSerializer, StudentProgressSerializer
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
