from rest_framework import serializers
from drf_spectacular.utils import extend_schema_field
from .models import (
    Category, Course, Module, VideoLesson, StudentProgress,
    Assignment, Quiz, QuizQuestion, QuizChoice, AssignmentSubmission,
    QuizAttempt, QuizAnswer, ModuleProgress
)

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
        return obj.courses.filter(is_published=True, allow_public_enrollment=True).count()

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
    assignments = serializers.SerializerMethodField()
    quizzes = serializers.SerializerMethodField()
    lesson_count = serializers.SerializerMethodField()
    progress = serializers.SerializerMethodField()
    
    class Meta:
        model = Module
        fields = ['id', 'title', 'order', 'lesson_count', 'video_lessons', 'assignments', 'quizzes', 'progress']
    
    @extend_schema_field(serializers.IntegerField)
    def get_lesson_count(self, obj):
        return obj.video_lessons.count()
    
    @extend_schema_field(serializers.ListField)
    def get_assignments(self, obj):
        assignments = obj.assignments.all().order_by('order')
        # We'll define AssignmentSerializer later in the file
        from apps.courses.serializers import AssignmentSerializer
        return AssignmentSerializer(assignments, many=True, context=self.context).data
    
    @extend_schema_field(serializers.ListField)
    def get_quizzes(self, obj):
        quizzes = obj.quizzes.all().order_by('order')
        # We'll define QuizSerializer later in the file  
        from apps.courses.serializers import QuizSerializer
        return QuizSerializer(quizzes, many=True, context=self.context).data
    
    @extend_schema_field(serializers.DictField)
    def get_progress(self, obj):
        request = self.context.get('request')
        if not request or not request.user.is_authenticated:
            return None
        
        try:
            progress = obj.student_progress.get(student=request.user)
            return {
                'is_unlocked': progress.is_unlocked,
                'is_completed': progress.is_completed,
                'completion_percentage': float(progress.completion_percentage),
                'videos_completed': progress.videos_completed,
                'assignments_completed': progress.assignments_completed,
                'quizzes_passed': progress.quizzes_passed
            }
        except ModuleProgress.DoesNotExist:
            return {
                'is_unlocked': False,
                'is_completed': False,
                'completion_percentage': 0.0,
                'videos_completed': 0,
                'assignments_completed': 0,
                'quizzes_passed': 0
            }

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
    thumbnail_url = serializers.SerializerMethodField()
    preview_video_url = serializers.SerializerMethodField()
    
    class Meta:
        model = Course
        fields = [
            'id', 'title', 'description', 'category_name', 'price', 'tax_rate',
            'price_display', 'total_price_display', 'is_free_course', 'thumbnail',
            'thumbnail_url', 'preview_video', 'preview_video_url', 'is_enrolled', 
            'module_count', 'total_lessons', 'allow_public_enrollment', 'created_at'
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
    
    @extend_schema_field(serializers.CharField)
    def get_thumbnail_url(self, obj):
        """Get full URL for thumbnail image"""
        if obj.thumbnail:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.thumbnail.url)
            return obj.thumbnail.url
        return None
    
    @extend_schema_field(serializers.CharField)
    def get_preview_video_url(self, obj):
        """Get preview video URL"""
        return obj.preview_video if obj.preview_video else None

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
    thumbnail_url = serializers.SerializerMethodField()
    preview_video_url = serializers.SerializerMethodField()
    
    class Meta:
        model = Course
        fields = [
            'id', 'title', 'description', 'category', 'price', 'tax_rate',
            'price_display', 'total_price_display', 'is_free_course', 'thumbnail',
            'thumbnail_url', 'preview_video', 'preview_video_url', 'is_published',
            'allow_public_enrollment', 'created_by_name', 'modules', 'is_enrolled', 
            'enrollment_info', 'created_at'
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
    
    @extend_schema_field(serializers.CharField)
    def get_thumbnail_url(self, obj):
        """Get full URL for thumbnail image"""
        if obj.thumbnail:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.thumbnail.url)
            return obj.thumbnail.url
        return None
    
    @extend_schema_field(serializers.CharField)
    def get_preview_video_url(self, obj):
        """Get preview video URL"""
        return obj.preview_video if obj.preview_video else None

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


# Assignment and Quiz Serializers

class AssignmentSerializer(serializers.ModelSerializer):
    """
    Serializer for assignments
    """
    module_title = serializers.CharField(source='module.title', read_only=True)
    course_title = serializers.CharField(source='module.course.title', read_only=True)
    submission_status = serializers.SerializerMethodField()
    user_submission = serializers.SerializerMethodField()
    
    class Meta:
        model = Assignment
        fields = [
            'id', 'title', 'description', 'requirements', 'resources',
            'max_points', 'passing_score', 'due_days', 'is_required', 
            'order', 'module_title', 'course_title', 'submission_status',
            'user_submission', 'created_at'
        ]
        read_only_fields = ['id', 'created_at']
    
    @extend_schema_field(serializers.CharField)
    def get_submission_status(self, obj):
        request = self.context.get('request')
        if not request or not request.user.is_authenticated:
            return 'not_submitted'
        
        try:
            submission = obj.submissions.get(student=request.user)
            return submission.status
        except AssignmentSubmission.DoesNotExist:
            return 'not_submitted'
    
    @extend_schema_field(serializers.DictField)
    def get_user_submission(self, obj):
        request = self.context.get('request')
        if not request or not request.user.is_authenticated:
            return None
        
        try:
            submission = obj.submissions.get(student=request.user)
            return {
                'id': submission.id,
                'github_url': submission.github_url,
                'submission_notes': submission.submission_notes,
                'status': submission.status,
                'score': submission.score,
                'grade_comments': submission.grade_comments,
                'submitted_at': submission.submitted_at,
                'graded_at': submission.graded_at
            }
        except AssignmentSubmission.DoesNotExist:
            return None


class AssignmentSubmissionSerializer(serializers.ModelSerializer):
    """
    Serializer for assignment submissions
    """
    assignment_title = serializers.CharField(source='assignment.title', read_only=True)
    student_name = serializers.SerializerMethodField()
    score_percentage = serializers.ReadOnlyField()
    is_passed = serializers.ReadOnlyField()
    
    class Meta:
        model = AssignmentSubmission
        fields = [
            'id', 'assignment', 'assignment_title', 'student_name',
            'github_url', 'submission_notes', 'status', 'score',
            'grade_comments', 'graded_by', 'score_percentage', 'is_passed',
            'submitted_at', 'graded_at', 'created_at'
        ]
        read_only_fields = [
            'id', 'student', 'assignment_title', 'student_name', 
            'score_percentage', 'is_passed', 'graded_by', 'submitted_at', 
            'graded_at', 'created_at'
        ]
    
    @extend_schema_field(serializers.CharField)
    def get_student_name(self, obj):
        return obj.student.name if hasattr(obj.student, 'name') else obj.student.username
    
    def create(self, validated_data):
        validated_data['student'] = self.context['request'].user
        return super().create(validated_data)
    
    def update(self, instance, validated_data):
        # Students can only update if status is draft
        if instance.status != 'draft':
            raise serializers.ValidationError("Cannot modify submitted assignment")
        return super().update(instance, validated_data)


class QuizChoiceSerializer(serializers.ModelSerializer):
    """
    Serializer for quiz choices
    """
    class Meta:
        model = QuizChoice
        fields = ['id', 'choice_text', 'order']
        # Note: is_correct is intentionally excluded for security


class QuizQuestionSerializer(serializers.ModelSerializer):
    """
    Serializer for quiz questions
    """
    choices = QuizChoiceSerializer(many=True, read_only=True)
    
    class Meta:
        model = QuizQuestion
        fields = [
            'id', 'question_text', 'question_type', 'points', 
            'explanation', 'order', 'choices'
        ]
        read_only_fields = ['id', 'explanation']  # Explanation shown only after answering


class QuizSerializer(serializers.ModelSerializer):
    """
    Serializer for quizzes
    """
    module_title = serializers.CharField(source='module.title', read_only=True)
    course_title = serializers.CharField(source='module.course.title', read_only=True)
    questions = QuizQuestionSerializer(many=True, read_only=True)
    user_attempts = serializers.SerializerMethodField()
    can_attempt = serializers.SerializerMethodField()
    best_score = serializers.SerializerMethodField()
    
    class Meta:
        model = Quiz
        fields = [
            'id', 'title', 'description', 'time_limit', 'max_attempts',
            'passing_score', 'is_required', 'randomize_questions',
            'show_results_immediately', 'order', 'module_title', 
            'course_title', 'total_questions', 'total_points',
            'questions', 'user_attempts', 'can_attempt', 'best_score',
            'created_at'
        ]
        read_only_fields = ['id', 'total_questions', 'total_points', 'created_at']
    
    @extend_schema_field(serializers.IntegerField)
    def get_user_attempts(self, obj):
        request = self.context.get('request')
        if not request or not request.user.is_authenticated:
            return 0
        
        return obj.attempts.filter(student=request.user, completed=True).count()
    
    @extend_schema_field(serializers.BooleanField)
    def get_can_attempt(self, obj):
        request = self.context.get('request')
        if not request or not request.user.is_authenticated:
            return False
        
        user_attempts = obj.attempts.filter(student=request.user, completed=True).count()
        return user_attempts < obj.max_attempts
    
    @extend_schema_field(serializers.FloatField)
    def get_best_score(self, obj):
        request = self.context.get('request')
        if not request or not request.user.is_authenticated:
            return None
        
        best_attempt = obj.attempts.filter(
            student=request.user, completed=True
        ).order_by('-score').first()
        
        return best_attempt.score_percentage if best_attempt else None


class QuizAttemptSerializer(serializers.ModelSerializer):
    """
    Serializer for quiz attempts
    """
    quiz_title = serializers.CharField(source='quiz.title', read_only=True)
    student_name = serializers.SerializerMethodField()
    score_percentage = serializers.ReadOnlyField()
    is_passed = serializers.ReadOnlyField()
    time_taken_display = serializers.SerializerMethodField()
    
    class Meta:
        model = QuizAttempt
        fields = [
            'id', 'quiz', 'quiz_title', 'student_name', 'attempt_number',
            'score', 'total_points', 'score_percentage', 'is_passed',
            'time_taken', 'time_taken_display', 'completed',
            'started_at', 'completed_at'
        ]
        read_only_fields = [
            'id', 'quiz_title', 'student_name', 'attempt_number',
            'score_percentage', 'is_passed', 'time_taken_display',
            'started_at', 'completed_at'
        ]
    
    @extend_schema_field(serializers.CharField)
    def get_student_name(self, obj):
        return obj.student.name if hasattr(obj.student, 'name') else obj.student.username
    
    @extend_schema_field(serializers.CharField)
    def get_time_taken_display(self, obj):
        if not obj.time_taken:
            return "N/A"
        minutes, seconds = divmod(obj.time_taken, 60)
        return f"{minutes}m {seconds}s"


class QuizAnswerSerializer(serializers.ModelSerializer):
    """
    Serializer for quiz answers
    """
    question_text = serializers.CharField(source='question.question_text', read_only=True)
    selected_choice_text = serializers.CharField(source='selected_choice.choice_text', read_only=True)
    
    class Meta:
        model = QuizAnswer
        fields = [
            'id', 'question', 'question_text', 'selected_choice', 
            'selected_choice_text', 'text_answer', 'is_correct', 'points_earned'
        ]
        read_only_fields = ['id', 'is_correct', 'points_earned']


class ModuleProgressSerializer(serializers.ModelSerializer):
    """
    Serializer for module progress
    """
    module_title = serializers.CharField(source='module.title', read_only=True)
    course_title = serializers.CharField(source='module.course.title', read_only=True)
    student_name = serializers.SerializerMethodField()
    
    class Meta:
        model = ModuleProgress
        fields = [
            'id', 'student_name', 'module_title', 'course_title',
            'videos_completed', 'assignments_completed', 'quizzes_passed',
            'is_unlocked', 'is_completed', 'completion_percentage',
            'started_at', 'completed_at'
        ]
        read_only_fields = [
            'id', 'videos_completed', 'assignments_completed', 
            'quizzes_passed', 'completion_percentage', 'started_at', 
            'completed_at'
        ]
    
    @extend_schema_field(serializers.CharField)
    def get_student_name(self, obj):
        return obj.student.name if hasattr(obj.student, 'name') else obj.student.username