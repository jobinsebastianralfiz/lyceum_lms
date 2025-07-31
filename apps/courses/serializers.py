from rest_framework import serializers
from drf_spectacular.utils import extend_schema_field
from .models import Category, Course, Module, VideoLesson, StudentProgress

class CategorySerializer(serializers.ModelSerializer):
    """
    Serializer for course categories
    """
    course_count = serializers.SerializerMethodField()
    
    class Meta:
        model = Category
        fields = ['id', 'name', 'description', 'course_count', 'created_at']
        read_only_fields = ['id', 'created_at']
    
    @extend_schema_field(serializers.IntegerField)
    def get_course_count(self, obj):
        return obj.courses.filter(is_published=True).count()

class VideoLessonSerializer(serializers.ModelSerializer):
    """
    Serializer for video lessons
    """
    duration_display = serializers.SerializerMethodField()
    can_access = serializers.SerializerMethodField()
    
    class Meta:
        model = VideoLesson
        fields = [
            'id', 'title', 'youtube_video_id', 'youtube_url', 
            'thumbnail_url', 'duration', 'duration_display', 
            'description', 'order', 'is_preview', 'can_access'
        ]
    
    @extend_schema_field(serializers.CharField)
    def get_duration_display(self, obj):
        """Convert seconds to MM:SS format"""
        if not obj.duration:
            return "00:00"
        minutes, seconds = divmod(obj.duration, 60)
        return f"{minutes:02d}:{seconds:02d}"
    
    @extend_schema_field(serializers.BooleanField)
    def get_can_access(self, obj):
        """Check if current user can access this video"""
        request = self.context.get('request')
        if not request or not request.user.is_authenticated:
            return obj.is_preview
        
        # Check if user is enrolled in the course
        from apps.payments.models import Enrollment
        is_enrolled = Enrollment.objects.filter(
            user=request.user,
            course=obj.module.course,
            active=True
        ).exists()
        
        return is_enrolled or obj.is_preview

class ModuleSerializer(serializers.ModelSerializer):
    """
    Serializer for course modules
    """
    video_lessons = VideoLessonSerializer(many=True, read_only=True)
    lesson_count = serializers.SerializerMethodField()
    
    class Meta:
        model = Module
        fields = ['id', 'title', 'order', 'lesson_count', 'video_lessons']
    
    @extend_schema_field(serializers.IntegerField)
    def get_lesson_count(self, obj):
        return obj.video_lessons.count()

class CourseListSerializer(serializers.ModelSerializer):
    """
    Serializer for course list view
    """
    category_name = serializers.CharField(source='category.name', read_only=True)
    price_display = serializers.CharField(read_only=True)
    total_price_display = serializers.CharField(read_only=True)
    is_enrolled = serializers.SerializerMethodField()
    module_count = serializers.SerializerMethodField()
    total_lessons = serializers.SerializerMethodField()
    
    class Meta:
        model = Course
        fields = [
            'id', 'title', 'description', 'category_name', 'price', 'tax_rate',
            'price_display', 'total_price_display', 'is_free_course', 'thumbnail',
            'preview_video', 'is_enrolled', 'module_count', 'total_lessons', 'created_at'
        ]
    
    @extend_schema_field(serializers.BooleanField)
    def get_is_enrolled(self, obj):
        request = self.context.get('request')
        if not request or not request.user.is_authenticated:
            return False
        
        from apps.payments.models import Enrollment
        return Enrollment.objects.filter(
            user=request.user,
            course=obj,
            active=True
        ).exists()
    
    @extend_schema_field(serializers.IntegerField)
    def get_module_count(self, obj):
        return obj.modules.count()
    
    @extend_schema_field(serializers.IntegerField) 
    def get_total_lessons(self, obj):
        return VideoLesson.objects.filter(module__course=obj).count()

class CourseDetailSerializer(serializers.ModelSerializer):
    """
    Serializer for detailed course view
    """
    category = CategorySerializer(read_only=True)
    modules = ModuleSerializer(many=True, read_only=True)
    created_by_name = serializers.CharField(source='created_by.name', read_only=True)
    price_display = serializers.CharField(read_only=True)
    total_price_display = serializers.CharField(read_only=True)
    is_enrolled = serializers.SerializerMethodField()
    enrollment_info = serializers.SerializerMethodField()
    
    class Meta:
        model = Course
        fields = [
            'id', 'title', 'description', 'category', 'price', 'tax_rate',
            'price_display', 'total_price_display', 'is_free_course', 'thumbnail',
            'preview_video', 'is_published', 'created_by_name', 'modules',
            'is_enrolled', 'enrollment_info', 'created_at'
        ]
    
    @extend_schema_field(serializers.BooleanField)
    def get_is_enrolled(self, obj):
        request = self.context.get('request')
        if not request or not request.user.is_authenticated:
            return False
        
        from apps.payments.models import Enrollment
        return Enrollment.objects.filter(
            user=request.user,
            course=obj,
            active=True
        ).exists()
    
    @extend_schema_field(serializers.DictField)
    def get_enrollment_info(self, obj):
        request = self.context.get('request')
        if not request or not request.user.is_authenticated:
            return None
        
        from apps.payments.models import Enrollment
        enrollment = Enrollment.objects.filter(
            user=request.user,
            course=obj,
            active=True
        ).first()
        
        if not enrollment:
            return None
        
        return {
            'enrolled_on': enrollment.enrolled_on,
            'payment_status': enrollment.payment_status,
            'total_amount': enrollment.total_amount,
            'outstanding_amount': enrollment.outstanding_amount
        }

class StudentProgressSerializer(serializers.ModelSerializer):
    """
    Serializer for student progress tracking
    """
    video_title = serializers.CharField(source='video_lesson.title', read_only=True)
    course_title = serializers.CharField(source='course.title', read_only=True)
    
    class Meta:
        model = StudentProgress
        fields = [
            'id', 'course_title', 'video_title', 'completed_percentage',
            'completed', 'last_watched_at'
        ]
        read_only_fields = ['id', 'course_title', 'video_title', 'last_watched_at']