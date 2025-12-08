from rest_framework import serializers
from drf_spectacular.utils import extend_schema_field
from .models import (
    Category, Course, Module, VideoLesson, StudentProgress,
    Assignment, Quiz, QuizQuestion, QuizChoice, AssignmentSubmission,
    QuizAttempt, QuizAnswer, ModuleProgress, PDFNote, Certificate,
    DailyStreak, DailyActivity
)


class InstructorSerializer(serializers.Serializer):
    """
    Serializer for instructor/teacher info displayed on courses.
    """
    id = serializers.IntegerField(read_only=True)
    name = serializers.SerializerMethodField()
    photo_url = serializers.SerializerMethodField()
    designation = serializers.CharField(read_only=True)
    specialization = serializers.CharField(read_only=True)
    bio = serializers.CharField(read_only=True)
    experience_years = serializers.IntegerField(read_only=True)
    qualification = serializers.CharField(read_only=True)

    @extend_schema_field(serializers.CharField)
    def get_name(self, obj):
        return obj.user.name if obj and obj.user else None

    @extend_schema_field(serializers.CharField)
    def get_photo_url(self, obj):
        if obj and obj.profile_photo:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.profile_photo.url)
            return obj.profile_photo.url
        return None


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
    Serializer for video lessons (backward compatible with Flutter app)
    """
    duration_display = serializers.SerializerMethodField()
    can_access = serializers.SerializerMethodField()
    resource_file_url = serializers.SerializerMethodField()
    order = serializers.SerializerMethodField()  # Now comes from ModuleVideo
    assignments = serializers.SerializerMethodField()
    quizzes = serializers.SerializerMethodField()
    pdf_notes = serializers.SerializerMethodField()

    # New fields for enhanced functionality
    platform = serializers.CharField(read_only=True)
    video_url = serializers.URLField(read_only=True)
    embed_url = serializers.SerializerMethodField()
    vimeo_video_id = serializers.CharField(read_only=True)

    class Meta:
        model = VideoLesson
        fields = [
            # Legacy fields (for Flutter compatibility)
            'id', 'title', 'youtube_video_id', 'youtube_url',
            'thumbnail_url', 'duration', 'duration_display',
            'description', 'order', 'is_preview', 'can_access',
            'resource_file_url',
            # New fields (optional for Flutter)
            'platform', 'video_url', 'embed_url', 'vimeo_video_id',
            # Multi-level content
            'assignments', 'quizzes', 'pdf_notes'
        ]

    @extend_schema_field(serializers.IntegerField)
    def get_order(self, obj):
        """Get order from context (ModuleVideo) if available"""
        module_video = self.context.get('module_video')
        if module_video:
            return module_video.order
        # Fallback for compatibility
        return 1

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
        if not request or not hasattr(request, 'user') or not request.user or not request.user.is_authenticated:
            return obj.is_preview

        # Check if user is enrolled in any course containing this video's modules
        from apps.payments.services import EnrollmentService
        # Get first module this video belongs to
        first_module = obj.modules.first()
        if not first_module:
            return obj.is_preview

        first_course = first_module.courses.first()
        if not first_course:
            return obj.is_preview

        is_enrolled = EnrollmentService.is_user_enrolled(request.user, first_course)

        return is_enrolled or obj.is_preview
    
    @extend_schema_field(serializers.CharField)
    def get_resource_file_url(self, obj):
        """Get full URL for resource file"""
        if obj.resource_file:
            request = self.context.get('request')
            if request:
                try:
                    return request.build_absolute_uri(obj.resource_file.url)
                except:
                    # Fallback if build_absolute_uri fails
                    return obj.resource_file.url
            return obj.resource_file.url
        return None
    
    @extend_schema_field(serializers.CharField)
    def get_embed_url(self, obj):
        """Get embeddable URL for the video"""
        return obj.embed_url

    @extend_schema_field(serializers.ListField)
    def get_assignments(self, obj):
        """Get assignments linked to this video"""
        assignment_links = obj.assignment_links.select_related('assignment').order_by('order')
        from apps.courses.serializers import AssignmentSerializer
        assignments_data = []
        for link in assignment_links:
            context = self.context.copy()
            context['video_assignment'] = link
            serializer = AssignmentSerializer(link.assignment, context=context)
            assignments_data.append(serializer.data)
        return assignments_data

    @extend_schema_field(serializers.ListField)
    def get_quizzes(self, obj):
        """Get quizzes linked to this video"""
        quiz_links = obj.quiz_links.select_related('quiz').order_by('order')
        from apps.courses.serializers import QuizSerializer
        quizzes_data = []
        for link in quiz_links:
            context = self.context.copy()
            context['video_quiz'] = link
            serializer = QuizSerializer(link.quiz, context=context)
            quizzes_data.append(serializer.data)
        return quizzes_data

    @extend_schema_field(serializers.ListField)
    def get_pdf_notes(self, obj):
        """Get PDF notes linked to this video"""
        pdf_links = obj.pdf_links.select_related('pdf_note').order_by('order')
        from apps.courses.serializers import PDFNoteSerializer
        pdfs_data = []
        for link in pdf_links:
            context = self.context.copy()
            context['video_pdf'] = link
            serializer = PDFNoteSerializer(link.pdf_note, context=context)
            pdfs_data.append(serializer.data)
        return pdfs_data

class ModuleSerializer(serializers.ModelSerializer):
    """
    Serializer for course modules
    """
    video_lessons = serializers.SerializerMethodField()
    assignments = serializers.SerializerMethodField()
    quizzes = serializers.SerializerMethodField()
    pdf_notes = serializers.SerializerMethodField()
    lesson_count = serializers.SerializerMethodField()
    progress = serializers.SerializerMethodField()
    order = serializers.SerializerMethodField()  # Now comes from CourseModule

    class Meta:
        model = Module
        fields = ['id', 'title', 'order', 'lesson_count', 'video_lessons', 'assignments', 'quizzes', 'pdf_notes', 'progress']

    @extend_schema_field(serializers.IntegerField)
    def get_order(self, obj):
        """Get order from context (CourseModule) if available"""
        course_module = self.context.get('course_module')
        if course_module:
            return course_module.order
        # Fallback for compatibility
        return 1

    @extend_schema_field(serializers.IntegerField)
    def get_lesson_count(self, obj):
        return obj.module_videos.count()

    @extend_schema_field(serializers.ListField)
    def get_video_lessons(self, obj):
        """Get video lessons with proper ordering from ModuleVideo"""
        video_links = obj.video_links.select_related('video_lesson').order_by('order')
        videos_data = []
        for link in video_links:
            context = self.context.copy()
            context['module_video'] = link
            serializer = VideoLessonSerializer(link.video_lesson, context=context)
            videos_data.append(serializer.data)
        return videos_data

    @extend_schema_field(serializers.ListField)
    def get_assignments(self, obj):
        assignment_links = obj.assignment_links.select_related('assignment').order_by('order')
        from apps.courses.serializers import AssignmentSerializer
        assignments_data = []
        for link in assignment_links:
            context = self.context.copy()
            context['module_assignment'] = link
            serializer = AssignmentSerializer(link.assignment, context=context)
            assignments_data.append(serializer.data)
        return assignments_data

    @extend_schema_field(serializers.ListField)
    def get_quizzes(self, obj):
        quiz_links = obj.quiz_links.select_related('quiz').order_by('order')
        from apps.courses.serializers import QuizSerializer
        quizzes_data = []
        for link in quiz_links:
            context = self.context.copy()
            context['module_quiz'] = link
            serializer = QuizSerializer(link.quiz, context=context)
            quizzes_data.append(serializer.data)
        return quizzes_data

    @extend_schema_field(serializers.ListField)
    def get_pdf_notes(self, obj):
        pdf_links = obj.pdf_links.select_related('pdf_note').order_by('order')
        from apps.courses.serializers import PDFNoteSerializer
        pdfs_data = []
        for link in pdf_links:
            context = self.context.copy()
            context['module_pdf'] = link
            serializer = PDFNoteSerializer(link.pdf_note, context=context)
            pdfs_data.append(serializer.data)
        return pdfs_data

    @extend_schema_field(serializers.DictField)
    def get_progress(self, obj):
        request = self.context.get('request')
        if not request or not hasattr(request, 'user') or not request.user or not request.user.is_authenticated:
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
    Serializer for course list view.
    Includes enrollment type fields for Flutter app to determine how to display courses.
    """
    category_name = serializers.CharField(source='category.name', read_only=True)
    price_display = serializers.CharField(read_only=True)
    total_price_display = serializers.CharField(read_only=True)
    is_enrolled = serializers.SerializerMethodField()
    module_count = serializers.SerializerMethodField()
    total_lessons = serializers.SerializerMethodField()
    thumbnail_url = serializers.SerializerMethodField()
    preview_video_url = serializers.SerializerMethodField()
    rating = serializers.SerializerMethodField()
    enrolled_count = serializers.SerializerMethodField()
    level = serializers.SerializerMethodField()
    duration = serializers.SerializerMethodField()
    instructor = serializers.SerializerMethodField()

    # New enrollment type fields
    enrollment_type = serializers.CharField(read_only=True)
    enrollment_type_display = serializers.CharField(read_only=True)
    can_purchase_online = serializers.BooleanField(read_only=True)
    is_enquiry_only = serializers.BooleanField(read_only=True)
    is_admin_only = serializers.BooleanField(read_only=True)

    # Schedule/batch info fields
    course_duration = serializers.CharField(source='duration', read_only=True)
    start_date = serializers.DateField(read_only=True)
    batch_info = serializers.CharField(read_only=True)

    class Meta:
        model = Course
        fields = [
            'id', 'title', 'description', 'curriculum', 'what_you_will_learn',
            'category_name', 'price', 'tax_rate', 'price_display', 'total_price_display',
            'is_free_course', 'thumbnail', 'thumbnail_url', 'preview_video',
            'preview_video_url', 'is_enrolled', 'module_count', 'total_lessons',
            'allow_public_enrollment', 'rating', 'enrolled_count', 'level', 'duration',
            'instructor',
            # New fields
            'enrollment_type', 'enrollment_type_display', 'can_purchase_online',
            'is_enquiry_only', 'is_admin_only', 'course_duration', 'start_date', 'batch_info',
            'created_at'
        ]
    
    @extend_schema_field(serializers.BooleanField)
    def get_is_enrolled(self, obj):
        request = self.context.get('request')
        if not request or not hasattr(request, 'user') or not request.user or not request.user.is_authenticated:
            return False
        
        from apps.payments.services import EnrollmentService
        return EnrollmentService.is_user_enrolled(request.user, obj)
    
    @extend_schema_field(serializers.IntegerField)
    def get_module_count(self, obj):
        return obj.modules.count()
    
    @extend_schema_field(serializers.IntegerField)
    def get_total_lessons(self, obj):
        # Count videos across all modules in this course
        total = 0
        for module_link in obj.module_links.all():
            total += module_link.module.module_videos.count()
        return total
    
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
    
    @extend_schema_field(serializers.FloatField)
    def get_rating(self, obj):
        """Get average rating for this course"""
        from apps.ratings.models import CourseRating
        ratings = CourseRating.objects.filter(course=obj, is_approved=True)
        if ratings.exists():
            from django.db.models import Avg
            avg_rating = ratings.aggregate(avg=Avg('rating'))['avg']
            return round(float(avg_rating), 1) if avg_rating else 0.0
        return 0.0
    
    @extend_schema_field(serializers.IntegerField)
    def get_enrolled_count(self, obj):
        """Get number of enrolled students"""
        from apps.payments.models import Enrollment
        return Enrollment.objects.filter(
            course=obj,
            active=True,
            payment_status__in=['completed', 'free', 'partial']  # Count all active enrollments
        ).count()
    
    @extend_schema_field(serializers.CharField)
    def get_level(self, obj):
        """Get course difficulty level based on modules"""
        modules = obj.modules.all()
        
        if not modules:
            return 'beginner'
        
        # Get the most common difficulty level from modules
        difficulty_counts = {}
        for module in modules:
            level = getattr(module, 'difficulty_level', 'beginner')
            difficulty_counts[level] = difficulty_counts.get(level, 0) + 1
        
        if not difficulty_counts:
            return 'beginner'
        
        # Return the most common difficulty level
        return max(difficulty_counts, key=difficulty_counts.get)
    
    @extend_schema_field(serializers.IntegerField)
    def get_duration(self, obj):
        """Get total course duration in minutes"""
        total_duration = 0
        modules = obj.modules.all()

        for module in modules:
            # Add module estimated duration if available
            if hasattr(module, 'duration_minutes') and module.duration_minutes:
                total_duration += module.duration_minutes
            else:
                # Calculate from video lessons duration (using through model)
                video_links = module.video_links.all()
                for video_link in video_links:
                    lesson = video_link.video_lesson
                    if lesson.duration:  # duration in seconds
                        total_duration += lesson.duration // 60  # convert to minutes

        return total_duration if total_duration > 0 else None

    @extend_schema_field(InstructorSerializer)
    def get_instructor(self, obj):
        """Get instructor info - teacher if assigned, otherwise fallback to created_by"""
        # First try to get the assigned teacher
        if obj.teacher:
            return InstructorSerializer(obj.teacher, context=self.context).data

        # Fallback: create basic instructor info from created_by
        if obj.created_by:
            return {
                'id': None,
                'name': obj.created_by.name if hasattr(obj.created_by, 'name') else obj.created_by.username,
                'photo_url': None,
                'designation': 'Instructor',
                'specialization': None,
                'bio': None,
                'experience_years': None,
                'qualification': None,
            }
        return None

class CourseDetailSerializer(serializers.ModelSerializer):
    """
    Serializer for detailed course view.
    Includes full enrollment type information and schedule details.
    """
    category = CategorySerializer(read_only=True)
    modules = serializers.SerializerMethodField()
    assignments = serializers.SerializerMethodField()
    quizzes = serializers.SerializerMethodField()
    pdf_notes = serializers.SerializerMethodField()
    created_by_name = serializers.CharField(source='created_by.name', read_only=True)
    price_display = serializers.CharField(read_only=True)
    total_price_display = serializers.CharField(read_only=True)
    is_enrolled = serializers.SerializerMethodField()
    enrollment_info = serializers.SerializerMethodField()
    thumbnail_url = serializers.SerializerMethodField()
    preview_video_url = serializers.SerializerMethodField()
    rating = serializers.SerializerMethodField()
    enrolled_count = serializers.SerializerMethodField()
    level = serializers.SerializerMethodField()
    duration = serializers.SerializerMethodField()
    instructor = serializers.SerializerMethodField()

    # Enrollment type fields
    enrollment_type = serializers.CharField(read_only=True)
    enrollment_type_display = serializers.CharField(read_only=True)
    can_purchase_online = serializers.BooleanField(read_only=True)
    is_enquiry_only = serializers.BooleanField(read_only=True)
    is_admin_only = serializers.BooleanField(read_only=True)

    # Schedule/batch info fields
    course_duration = serializers.CharField(source='duration', read_only=True)
    start_date = serializers.DateField(read_only=True)
    batch_info = serializers.CharField(read_only=True)

    class Meta:
        model = Course
        fields = [
            'id', 'title', 'description', 'curriculum', 'what_you_will_learn',
            'category', 'price', 'tax_rate', 'price_display', 'total_price_display',
            'is_free_course', 'thumbnail', 'thumbnail_url', 'preview_video',
            'preview_video_url', 'is_published', 'allow_public_enrollment',
            'created_by_name', 'modules', 'assignments', 'quizzes', 'pdf_notes',
            'is_enrolled', 'enrollment_info', 'rating', 'enrolled_count',
            'level', 'duration', 'instructor',
            # New enrollment type fields
            'enrollment_type', 'enrollment_type_display', 'can_purchase_online',
            'is_enquiry_only', 'is_admin_only', 'course_duration', 'start_date', 'batch_info',
            'created_at'
        ]
    
    @extend_schema_field(serializers.BooleanField)
    def get_is_enrolled(self, obj):
        request = self.context.get('request')
        if not request or not hasattr(request, 'user') or not request.user or not request.user.is_authenticated:
            return False
        
        from apps.payments.services import EnrollmentService
        return EnrollmentService.is_user_enrolled(request.user, obj)
    
    @extend_schema_field(serializers.DictField)
    def get_enrollment_info(self, obj):
        request = self.context.get('request')
        if not request or not hasattr(request, 'user') or not request.user or not request.user.is_authenticated:
            return None
        
        from apps.payments.services import EnrollmentService
        enrollment = EnrollmentService.get_user_enrollment(request.user, obj)
        
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
    
    @extend_schema_field(serializers.ListField)
    def get_modules(self, obj):
        """Get modules ordered by CourseModule order"""
        module_links = obj.module_links.select_related('module').filter(
            module__is_active=True
        ).order_by('order')

        modules_data = []
        for link in module_links:
            context = self.context.copy()
            context['course_module'] = link
            serializer = ModuleSerializer(link.module, context=context)
            modules_data.append(serializer.data)
        return modules_data

    @extend_schema_field(serializers.ListField)
    def get_assignments(self, obj):
        """Get course-level assignments ordered by CourseAssignment order"""
        assignment_links = obj.assignment_links.select_related('assignment').order_by('order')
        # AssignmentSerializer is defined later in this file, we'll use it directly
        assignments_data = []
        for link in assignment_links:
            assignment_data = {
                'id': link.assignment.id,
                'title': link.assignment.title,
                'description': link.assignment.description,
                'max_points': link.assignment.max_points,
                'passing_score': link.assignment.passing_score,
                'is_required': link.assignment.is_required,
                'order': link.order,
                'due_days': link.assignment.due_days,
                'created_at': link.assignment.created_at,
            }
            assignments_data.append(assignment_data)
        return assignments_data

    @extend_schema_field(serializers.ListField)
    def get_quizzes(self, obj):
        """Get course-level quizzes ordered by CourseQuiz order"""
        quiz_links = obj.quiz_links.select_related('quiz').order_by('order')
        quizzes_data = []
        for link in quiz_links:
            quiz_data = {
                'id': link.quiz.id,
                'title': link.quiz.title,
                'description': link.quiz.description,
                'time_limit': link.quiz.time_limit,
                'passing_score': link.quiz.passing_score,
                'max_attempts': link.quiz.max_attempts,
                'is_required': link.quiz.is_required,
                'order': link.order,
                'total_questions': link.quiz.questions.count() if hasattr(link.quiz, 'questions') else 0,
                'created_at': link.quiz.created_at,
            }
            quizzes_data.append(quiz_data)
        return quizzes_data

    @extend_schema_field(serializers.ListField)
    def get_pdf_notes(self, obj):
        """Get course-level PDF notes ordered by CoursePDF order"""
        pdf_links = obj.pdf_links.select_related('pdf_note').order_by('order')
        pdfs_data = []
        for link in pdf_links:
            pdf_url = None
            if link.pdf_note.pdf_file:
                request = self.context.get('request')
                if request:
                    pdf_url = request.build_absolute_uri(link.pdf_note.pdf_file.url)
                else:
                    pdf_url = link.pdf_note.pdf_file.url

            pdf_data = {
                'id': link.pdf_note.id,
                'title': link.pdf_note.title,
                'description': link.pdf_note.description,
                'pdf_url': pdf_url,
                'file_size': link.pdf_note.file_size,
                'page_count': link.pdf_note.page_count,
                'is_downloadable': link.pdf_note.is_downloadable,
                'order': link.order,
                'created_at': link.pdf_note.created_at,
            }
            pdfs_data.append(pdf_data)
        return pdfs_data

    @extend_schema_field(serializers.FloatField)
    def get_rating(self, obj):
        """Get average rating for this course"""
        from apps.ratings.models import CourseRating
        ratings = CourseRating.objects.filter(course=obj, is_approved=True)
        if ratings.exists():
            from django.db.models import Avg
            avg_rating = ratings.aggregate(avg=Avg('rating'))['avg']
            return round(float(avg_rating), 1) if avg_rating else 0.0
        return 0.0
    
    @extend_schema_field(serializers.IntegerField)
    def get_enrolled_count(self, obj):
        """Get number of enrolled students"""
        from apps.payments.models import Enrollment
        return Enrollment.objects.filter(
            course=obj,
            active=True,
            payment_status__in=['completed', 'free', 'partial']  # Count all active enrollments
        ).count()
    
    @extend_schema_field(serializers.CharField)
    def get_level(self, obj):
        """Get course difficulty level based on modules"""
        modules = obj.modules.all()
        
        if not modules:
            return 'beginner'
        
        # Get the most common difficulty level from modules
        difficulty_counts = {}
        for module in modules:
            level = getattr(module, 'difficulty_level', 'beginner')
            difficulty_counts[level] = difficulty_counts.get(level, 0) + 1
        
        if not difficulty_counts:
            return 'beginner'
        
        # Return the most common difficulty level
        return max(difficulty_counts, key=difficulty_counts.get)
    
    @extend_schema_field(serializers.IntegerField)
    def get_duration(self, obj):
        """Get total course duration in minutes"""
        total_duration = 0
        modules = obj.modules.all()
        
        for module in modules:
            # Add module estimated duration if available
            if hasattr(module, 'duration_minutes') and module.duration_minutes:
                total_duration += module.duration_minutes
            else:
                # Calculate from video lessons duration (using through model)
                video_links = module.video_links.all()
                for video_link in video_links:
                    lesson = video_link.video_lesson
                    if lesson.duration:  # duration in seconds
                        total_duration += lesson.duration // 60  # convert to minutes
        
        return total_duration if total_duration > 0 else None

    @extend_schema_field(InstructorSerializer)
    def get_instructor(self, obj):
        """Get instructor info - teacher if assigned, otherwise fallback to created_by"""
        # First try to get the assigned teacher
        if obj.teacher:
            return InstructorSerializer(obj.teacher, context=self.context).data

        # Fallback: create basic instructor info from created_by
        if obj.created_by:
            return {
                'id': None,
                'name': obj.created_by.name if hasattr(obj.created_by, 'name') else obj.created_by.username,
                'photo_url': None,
                'designation': 'Instructor',
                'specialization': None,
                'bio': None,
                'experience_years': None,
                'qualification': None,
            }
        return None

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
    Serializer for assignments (backward compatible with Flutter app)
    """
    module_title = serializers.SerializerMethodField()
    course_title = serializers.SerializerMethodField()
    submission_status = serializers.SerializerMethodField()
    user_submission = serializers.SerializerMethodField()
    order = serializers.SerializerMethodField()

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
    def get_module_title(self, obj):
        """Get first module title for backward compatibility"""
        module_assignment = self.context.get('module_assignment')
        if module_assignment:
            return module_assignment.module.title
        first_link = obj.module_links.select_related('module').first()
        return first_link.module.title if first_link else None

    @extend_schema_field(serializers.CharField)
    def get_course_title(self, obj):
        """Get first course title for backward compatibility"""
        module_assignment = self.context.get('module_assignment')
        if module_assignment:
            first_course_link = module_assignment.module.course_links.select_related('course').first()
            return first_course_link.course.title if first_course_link else None

        first_link = obj.module_links.select_related('module__course_links__course').first()
        if first_link and first_link.module.course_links.exists():
            first_course_link = first_link.module.course_links.first()
            return first_course_link.course.title
        return None

    @extend_schema_field(serializers.IntegerField)
    def get_order(self, obj):
        """Get order from context based on link type"""
        # Check for course assignment
        course_assignment = self.context.get('course_assignment')
        if course_assignment:
            return course_assignment.order

        # Check for module assignment
        module_assignment = self.context.get('module_assignment')
        if module_assignment:
            return module_assignment.order

        # Check for video assignment
        video_assignment = self.context.get('video_assignment')
        if video_assignment:
            return video_assignment.order

        # Fallback to first module link
        first_link = obj.module_links.first()
        return first_link.order if first_link else 1
    
    @extend_schema_field(serializers.CharField)
    def get_submission_status(self, obj):
        request = self.context.get('request')
        if not request or not hasattr(request, 'user') or not request.user or not request.user.is_authenticated:
            return 'not_submitted'
        
        try:
            submission = obj.submissions.get(student=request.user)
            return submission.status
        except AssignmentSubmission.DoesNotExist:
            return 'not_submitted'
    
    @extend_schema_field(serializers.DictField)
    def get_user_submission(self, obj):
        request = self.context.get('request')
        if not request or not hasattr(request, 'user') or not request.user or not request.user.is_authenticated:
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
    Serializer for quizzes (backward compatible with Flutter app)
    """
    module_title = serializers.SerializerMethodField()
    course_title = serializers.SerializerMethodField()
    questions = QuizQuestionSerializer(many=True, read_only=True)
    user_attempts = serializers.SerializerMethodField()
    can_attempt = serializers.SerializerMethodField()
    best_score = serializers.SerializerMethodField()
    order = serializers.SerializerMethodField()

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

    @extend_schema_field(serializers.CharField)
    def get_module_title(self, obj):
        """Get first module title for backward compatibility"""
        module_quiz = self.context.get('module_quiz')
        if module_quiz:
            return module_quiz.module.title
        first_link = obj.module_links.select_related('module').first()
        return first_link.module.title if first_link else None

    @extend_schema_field(serializers.CharField)
    def get_course_title(self, obj):
        """Get first course title for backward compatibility"""
        module_quiz = self.context.get('module_quiz')
        if module_quiz:
            first_course_link = module_quiz.module.course_links.select_related('course').first()
            return first_course_link.course.title if first_course_link else None

        first_link = obj.module_links.select_related('module__course_links__course').first()
        if first_link and first_link.module.course_links.exists():
            first_course_link = first_link.module.course_links.first()
            return first_course_link.course.title
        return None

    @extend_schema_field(serializers.IntegerField)
    def get_order(self, obj):
        """Get order from context based on link type"""
        # Check for course quiz
        course_quiz = self.context.get('course_quiz')
        if course_quiz:
            return course_quiz.order

        # Check for module quiz
        module_quiz = self.context.get('module_quiz')
        if module_quiz:
            return module_quiz.order

        # Check for video quiz
        video_quiz = self.context.get('video_quiz')
        if video_quiz:
            return video_quiz.order

        # Fallback to first module link
        first_link = obj.module_links.first()
        return first_link.order if first_link else 1
    
    @extend_schema_field(serializers.IntegerField)
    def get_user_attempts(self, obj):
        request = self.context.get('request')
        if not request or not hasattr(request, 'user') or not request.user or not request.user.is_authenticated:
            return 0
        
        return obj.attempts.filter(student=request.user, completed=True).count()
    
    @extend_schema_field(serializers.BooleanField)
    def get_can_attempt(self, obj):
        request = self.context.get('request')
        if not request or not hasattr(request, 'user') or not request.user or not request.user.is_authenticated:
            return False
        
        user_attempts = obj.attempts.filter(student=request.user, completed=True).count()
        return user_attempts < obj.max_attempts
    
    @extend_schema_field(serializers.FloatField)
    def get_best_score(self, obj):
        request = self.context.get('request')
        if not request or not hasattr(request, 'user') or not request.user or not request.user.is_authenticated:
            return None
        
        best_attempt = obj.attempts.filter(
            student=request.user, completed=True
        ).order_by('-score').first()
        
        return best_attempt.score_percentage if best_attempt else None


class PDFNoteSerializer(serializers.ModelSerializer):
    """
    Serializer for PDF notes/documents
    """
    pdf_file_url = serializers.SerializerMethodField()
    file_size_display = serializers.SerializerMethodField()
    order = serializers.SerializerMethodField()

    class Meta:
        model = PDFNote
        fields = [
            'id', 'title', 'description', 'pdf_file', 'pdf_file_url',
            'file_size', 'file_size_display', 'page_count',
            'is_downloadable', 'order', 'created_at'
        ]
        read_only_fields = ['id', 'file_size', 'created_at']

    @extend_schema_field(serializers.CharField)
    def get_pdf_file_url(self, obj):
        """Get full URL for PDF file"""
        if obj.pdf_file:
            request = self.context.get('request')
            if request:
                try:
                    return request.build_absolute_uri(obj.pdf_file.url)
                except:
                    return obj.pdf_file.url
            return obj.pdf_file.url
        return None

    @extend_schema_field(serializers.CharField)
    def get_file_size_display(self, obj):
        """Get human-readable file size"""
        if not obj.file_size:
            return "N/A"
        # Convert bytes to MB
        size_mb = obj.file_size / (1024 * 1024)
        if size_mb < 1:
            size_kb = obj.file_size / 1024
            return f"{size_kb:.2f} KB"
        return f"{size_mb:.2f} MB"

    @extend_schema_field(serializers.IntegerField)
    def get_order(self, obj):
        """Get order from context based on link type"""
        # Check for course link
        course_pdf = self.context.get('course_pdf')
        if course_pdf:
            return course_pdf.order

        # Check for module link
        module_pdf = self.context.get('module_pdf')
        if module_pdf:
            return module_pdf.order

        # Check for video link
        video_pdf = self.context.get('video_pdf')
        if video_pdf:
            return video_pdf.order

        # Fallback
        return 1


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
    Serializer for module progress (backward compatible with Flutter app)
    """
    module_title = serializers.CharField(source='module.title', read_only=True)
    course_title = serializers.SerializerMethodField()
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
    def get_course_title(self, obj):
        """Get first course title for backward compatibility"""
        first_course_link = obj.module.course_links.select_related('course').first()
        return first_course_link.course.title if first_course_link else None

    @extend_schema_field(serializers.CharField)
    def get_student_name(self, obj):
        return obj.student.name if hasattr(obj.student, 'name') else obj.student.username


# ==================== CERTIFICATE SERIALIZERS ====================

class CertificateListSerializer(serializers.ModelSerializer):
    """
    Serializer for listing student certificates.
    Used in Flutter app for displaying certificate cards.
    """
    course_title = serializers.CharField(source='course.title', read_only=True)
    course_thumbnail = serializers.SerializerMethodField()
    student_name = serializers.CharField(source='student.name', read_only=True)
    certificate_type_display = serializers.CharField(source='get_certificate_type_display', read_only=True)
    pdf_url = serializers.SerializerMethodField()
    is_valid = serializers.SerializerMethodField()

    class Meta:
        model = Certificate
        fields = [
            'id', 'certificate_number', 'certificate_type', 'certificate_type_display',
            'title', 'course_title', 'course_thumbnail', 'student_name',
            'completion_date', 'issue_date', 'final_score', 'grade',
            'verification_code', 'pdf_url', 'is_valid', 'is_revoked'
        ]

    @extend_schema_field(serializers.CharField)
    def get_course_thumbnail(self, obj):
        if obj.course.thumbnail:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.course.thumbnail.url)
            return obj.course.thumbnail.url
        return None

    @extend_schema_field(serializers.CharField)
    def get_pdf_url(self, obj):
        # Generate PDF if it doesn't exist
        if not obj.pdf_file:
            try:
                from apps.courses.certificate_generator import generate_certificate_pdf
                from django.core.files.base import ContentFile

                pdf_buffer = generate_certificate_pdf(obj)
                pdf_filename = f"certificate_{obj.certificate_number}.pdf"
                obj.pdf_file.save(pdf_filename, ContentFile(pdf_buffer.getvalue()), save=True)
            except Exception:
                return None

        if obj.pdf_file:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.pdf_file.url)
            return obj.pdf_file.url
        return None

    @extend_schema_field(serializers.BooleanField)
    def get_is_valid(self, obj):
        return not obj.is_revoked


class CertificateDetailSerializer(serializers.ModelSerializer):
    """
    Detailed serializer for individual certificate view.
    Includes full course info and verification details.
    """
    course_title = serializers.CharField(source='course.title', read_only=True)
    course_description = serializers.CharField(source='course.description', read_only=True)
    course_thumbnail = serializers.SerializerMethodField()
    student_name = serializers.CharField(source='student.name', read_only=True)
    student_email = serializers.CharField(source='student.email', read_only=True)
    certificate_type_display = serializers.CharField(source='get_certificate_type_display', read_only=True)
    pdf_url = serializers.SerializerMethodField()
    is_valid = serializers.SerializerMethodField()
    verification_status = serializers.SerializerMethodField()

    class Meta:
        model = Certificate
        fields = [
            'id', 'certificate_number', 'certificate_type', 'certificate_type_display',
            'title', 'description', 'course', 'course_title', 'course_description',
            'course_thumbnail', 'student_name', 'student_email',
            'completion_date', 'issue_date', 'final_score', 'grade',
            'verification_code', 'verification_url', 'pdf_url',
            'signed_by', 'signed_by_title',
            'is_valid', 'is_revoked', 'revoked_reason', 'revoked_at',
            'verification_status', 'created_at'
        ]

    @extend_schema_field(serializers.CharField)
    def get_course_thumbnail(self, obj):
        if obj.course.thumbnail:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.course.thumbnail.url)
            return obj.course.thumbnail.url
        return None

    @extend_schema_field(serializers.CharField)
    def get_pdf_url(self, obj):
        # Generate PDF if it doesn't exist
        if not obj.pdf_file:
            try:
                from apps.courses.certificate_generator import generate_certificate_pdf
                from django.core.files.base import ContentFile

                pdf_buffer = generate_certificate_pdf(obj)
                pdf_filename = f"certificate_{obj.certificate_number}.pdf"
                obj.pdf_file.save(pdf_filename, ContentFile(pdf_buffer.getvalue()), save=True)
            except Exception:
                return None

        if obj.pdf_file:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.pdf_file.url)
            return obj.pdf_file.url
        return None

    @extend_schema_field(serializers.BooleanField)
    def get_is_valid(self, obj):
        return not obj.is_revoked

    @extend_schema_field(serializers.DictField)
    def get_verification_status(self, obj):
        return {
            'is_valid': not obj.is_revoked,
            'status': 'revoked' if obj.is_revoked else 'valid',
            'message': obj.revoked_reason if obj.is_revoked else 'This certificate is valid and verified.',
            'verified_at': obj.updated_at
        }


class CertificateVerificationSerializer(serializers.Serializer):
    """
    Serializer for certificate verification response.
    Used when verifying a certificate by code.
    """
    is_valid = serializers.BooleanField()
    status = serializers.CharField()
    message = serializers.CharField()

    # Certificate info (only if valid)
    certificate_number = serializers.CharField(required=False)
    student_name = serializers.CharField(required=False)
    course_title = serializers.CharField(required=False)
    completion_date = serializers.DateField(required=False)
    issue_date = serializers.DateField(required=False)
    certificate_type = serializers.CharField(required=False)
    grade = serializers.CharField(required=False, allow_null=True)
    signed_by = serializers.CharField(required=False, allow_null=True)
    signed_by_title = serializers.CharField(required=False, allow_null=True)


class CertificateSimpleSerializer(serializers.ModelSerializer):
    """
    Minimal certificate data for dashboard/lists.
    """
    course_title = serializers.CharField(source='course.title', read_only=True)

    class Meta:
        model = Certificate
        fields = [
            'id', 'certificate_number', 'course_title', 'issue_date', 'is_revoked'
        ]


# ==================== STREAK SERIALIZERS ====================

class DailyStreakSerializer(serializers.ModelSerializer):
    """
    Serializer for student daily streak data.
    Used for retrieving and displaying streak information.
    """
    student_name = serializers.CharField(source='student.name', read_only=True)
    is_active_today = serializers.SerializerMethodField()
    streak_status = serializers.SerializerMethodField()
    days_since_last_activity = serializers.SerializerMethodField()

    class Meta:
        model = DailyStreak
        fields = [
            'id', 'student_name', 'current_streak', 'longest_streak',
            'total_active_days', 'streak_start_date', 'last_activity_date',
            'is_active_today', 'streak_status', 'days_since_last_activity',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'student_name', 'created_at', 'updated_at']

    @extend_schema_field(serializers.BooleanField)
    def get_is_active_today(self, obj):
        from django.utils import timezone
        today = timezone.now().date()
        return obj.last_activity_date == today

    @extend_schema_field(serializers.CharField)
    def get_streak_status(self, obj):
        from django.utils import timezone
        from datetime import timedelta
        today = timezone.now().date()

        if obj.last_activity_date is None:
            return 'no_activity'
        elif obj.last_activity_date == today:
            return 'active'
        elif obj.last_activity_date == today - timedelta(days=1):
            return 'at_risk'  # Streak will break if no activity today
        else:
            return 'broken'

    @extend_schema_field(serializers.IntegerField)
    def get_days_since_last_activity(self, obj):
        from django.utils import timezone
        if obj.last_activity_date is None:
            return None
        return (timezone.now().date() - obj.last_activity_date).days


class DailyActivitySerializer(serializers.ModelSerializer):
    """
    Serializer for daily activity logs.
    """
    class Meta:
        model = DailyActivity
        fields = [
            'id', 'activity_date', 'activities_count', 'videos_watched',
            'quizzes_attempted', 'assignments_submitted', 'learning_minutes',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class DailyActivitySummarySerializer(serializers.Serializer):
    """
    Serializer for weekly/monthly activity summary.
    """
    date = serializers.DateField()
    activities_count = serializers.IntegerField()
    videos_watched = serializers.IntegerField()
    quizzes_attempted = serializers.IntegerField()
    assignments_submitted = serializers.IntegerField()
    learning_minutes = serializers.IntegerField()
    has_activity = serializers.BooleanField()


class RecordActivitySerializer(serializers.Serializer):
    """
    Serializer for recording a new activity.
    """
    activity_type = serializers.ChoiceField(
        choices=['video', 'quiz', 'assignment', 'general'],
        default='general',
        help_text="Type of activity being recorded"
    )
    minutes = serializers.IntegerField(
        default=0,
        min_value=0,
        help_text="Learning time in minutes (optional)"
    )


class StreakResponseSerializer(serializers.Serializer):
    """
    Response serializer for streak operations.
    """
    success = serializers.BooleanField()
    message = serializers.CharField()
    current_streak = serializers.IntegerField()
    longest_streak = serializers.IntegerField()
    total_active_days = serializers.IntegerField()
    is_active_today = serializers.BooleanField()
    streak_status = serializers.CharField()