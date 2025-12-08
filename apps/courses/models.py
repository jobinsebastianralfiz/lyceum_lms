from django.db import models
from django.conf import settings
from django.core.exceptions import ValidationError
from django.utils import timezone

class Category(models.Model):
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return self.name
    
    class Meta:
        db_table = 'categories'
        verbose_name_plural = 'Categories'

class Course(models.Model):
    # Enrollment Type Choices
    ENROLLMENT_TYPE_CHOICES = [
        ('online_purchase', 'Online Purchase'),  # Can buy from website/app
        ('admin_only', 'Admin Enrollment Only'),  # Only admin can enroll
        ('enquiry_only', 'Enquiry Only'),  # Information only, leads to enquiry form
    ]

    # Many-to-many with Module through CourseModule
    modules = models.ManyToManyField('Module', through='CourseModule', related_name='module_courses')

    title = models.CharField(max_length=200)
    description = models.TextField()
    category = models.ForeignKey(Category, on_delete=models.CASCADE, related_name='courses')
    price = models.DecimalField(max_digits=10, decimal_places=2, default=0.00, help_text="Price excluding tax (0 for free courses)")
    tax_rate = models.DecimalField(max_digits=5, decimal_places=2, default=18.0, help_text="Tax rate in percentage")
    is_free = models.BooleanField(default=False, help_text="Mark as true for free courses")
    thumbnail = models.ImageField(upload_to='course_thumbnails/', blank=True, null=True)
    preview_video = models.URLField(blank=True, null=True, help_text="YouTube video URL for preview")
    curriculum = models.TextField(blank=True, null=True, help_text="Detailed curriculum outline - what topics will be covered")
    what_you_will_learn = models.TextField(blank=True, null=True, help_text="Learning outcomes - what students will achieve after completing the course")
    is_published = models.BooleanField(default=False)

    # Enrollment settings
    enrollment_type = models.CharField(
        max_length=20,
        choices=ENROLLMENT_TYPE_CHOICES,
        default='online_purchase',
        help_text="How students can enroll in this course"
    )
    allow_public_enrollment = models.BooleanField(default=True, help_text="Allow students to enroll via app/API. If False, only admin can enroll students.")

    # Duration and schedule info (for enquiry courses)
    duration = models.CharField(max_length=100, blank=True, null=True, help_text="e.g., '6 months', '12 weeks'")
    start_date = models.DateField(blank=True, null=True, help_text="Next batch start date")
    batch_info = models.CharField(max_length=200, blank=True, null=True, help_text="e.g., 'Weekend Batch', 'Weekday Evening'")

    # Teacher assignment
    teacher = models.ForeignKey(
        'teachers.TeacherProfile',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='teaching_courses',
        help_text="Primary teacher/instructor for this course"
    )

    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='created_courses')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.title
    
    @property
    def is_free_course(self):
        """Check if course is free"""
        return self.is_free or (self.price is not None and self.price <= 0)
    
    @property
    def total_price(self):
        """Calculate total price including tax"""
        if self.is_free_course:
            return 0.00
        if self.price is None or self.tax_rate is None:
            return 0.00
        return self.price + (self.price * self.tax_rate / 100)
    
    @property
    def tax_amount(self):
        """Calculate tax amount"""
        if self.is_free_course:
            return 0.00
        if self.price is None or self.tax_rate is None:
            return 0.00
        return self.price * self.tax_rate / 100
    
    @property
    def price_display(self):
        """Display price with formatting"""
        if self.is_free_course:
            return "Free"
        return f"₹{self.price}"
    
    @property
    def total_price_display(self):
        """Display total price with formatting"""
        if self.is_free_course:
            return "Free"
        return f"₹{self.total_price:.2f}"

    @property
    def can_purchase_online(self):
        """Check if course can be purchased online"""
        return self.enrollment_type == 'online_purchase' and self.allow_public_enrollment

    @property
    def is_admin_only(self):
        """Check if course requires admin enrollment"""
        return self.enrollment_type == 'admin_only' or not self.allow_public_enrollment

    @property
    def is_enquiry_only(self):
        """Check if course is enquiry/information only"""
        return self.enrollment_type == 'enquiry_only'

    @property
    def enrollment_type_display(self):
        """Get human-readable enrollment type"""
        return dict(self.ENROLLMENT_TYPE_CHOICES).get(self.enrollment_type, self.enrollment_type)

    class Meta:
        db_table = 'courses'
        ordering = ['-created_at']

class Module(models.Model):
    """Reusable module that can be added to multiple courses"""
    DIFFICULTY_CHOICES = [
        ('beginner', 'Beginner'),
        ('intermediate', 'Intermediate'),
        ('advanced', 'Advanced'),
    ]

    # Many-to-many with Course through CourseModule
    courses = models.ManyToManyField('Course', through='CourseModule', related_name='course_modules')

    title = models.CharField(max_length=200)
    description = models.TextField(default="Module description not provided.")
    learning_objectives = models.TextField(blank=True, null=True, help_text="What students will learn")
    duration_minutes = models.PositiveIntegerField(blank=True, null=True, help_text="Estimated completion time")
    difficulty_level = models.CharField(max_length=20, choices=DIFFICULTY_CHOICES, default='beginner')
    is_active = models.BooleanField(default=True, help_text="Module is available to students")
    prerequisites = models.TextField(blank=True, null=True, help_text="Required knowledge or previous modules")
    passing_score_percentage = models.DecimalField(max_digits=5, decimal_places=2, default=70.0)
    max_attempts = models.PositiveIntegerField(blank=True, null=True, help_text="Maximum attempts allowed")
    requires_completion = models.BooleanField(default=True, help_text="Must complete to progress")
    resources = models.TextField(blank=True, null=True, help_text="Additional learning resources")
    tags = models.CharField(max_length=500, blank=True, null=True, help_text="Comma-separated tags")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.title

    def get_first_course(self):
        """Helper method to get first course (for backward compatibility)"""
        first_link = self.course_links.select_related('course').first()
        return first_link.course if first_link else None

    @property
    def course(self):
        """Property for backward compatibility - returns first course"""
        if not hasattr(self, '_cached_course'):
            self._cached_course = self.get_first_course()
        return self._cached_course

    class Meta:
        db_table = 'modules'
        ordering = ['title']


class CourseModule(models.Model):
    """Through model for Course-Module relationship with ordering"""
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name='module_links')
    module = models.ForeignKey(Module, on_delete=models.CASCADE, related_name='course_links')
    order = models.PositiveIntegerField(default=1, help_text="Order of module in this course")
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.course.title} - {self.module.title} (Order: {self.order})"

    class Meta:
        db_table = 'course_modules'
        ordering = ['course', 'order']
        unique_together = ['course', 'module']

class ModuleVideo(models.Model):
    """Through model for Module-VideoLesson relationship with ordering"""
    module = models.ForeignKey(Module, on_delete=models.CASCADE, related_name='video_links')
    video_lesson = models.ForeignKey('VideoLesson', on_delete=models.CASCADE, related_name='module_links')
    order = models.PositiveIntegerField(default=1, help_text="Order of video in this module")
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.module.title} - {self.video_lesson.title} (Order: {self.order})"

    class Meta:
        db_table = 'module_videos'
        ordering = ['module', 'order']
        unique_together = ['module', 'video_lesson']


class VideoLesson(models.Model):
    """Reusable video lesson that can be added to multiple modules"""
    PLATFORM_CHOICES = [
        ('youtube', 'YouTube'),
        ('vimeo', 'Vimeo'),
        ('direct', 'Direct URL'),
    ]

    # Many-to-many with Module through ModuleVideo
    modules = models.ManyToManyField(Module, through='ModuleVideo', related_name='module_videos')

    title = models.CharField(max_length=200)

    # Legacy fields (kept for backward compatibility)
    youtube_video_id = models.CharField(max_length=20, blank=True, null=True, help_text="YouTube video ID (legacy)")
    youtube_url = models.URLField(blank=True, null=True, help_text="Full YouTube URL (legacy)")

    # New platform-agnostic fields
    platform = models.CharField(max_length=20, choices=PLATFORM_CHOICES, default='youtube', help_text="Video platform")
    video_url = models.URLField(blank=True, null=True, help_text="Original video URL")
    video_id = models.CharField(max_length=50, blank=True, null=True, help_text="Platform-specific video ID")
    vimeo_video_id = models.CharField(max_length=20, blank=True, null=True, help_text="Vimeo video ID")

    # Metadata (can be auto-fetched or manual)
    thumbnail_url = models.URLField(blank=True, null=True)
    duration = models.PositiveIntegerField(default=0, help_text="Duration in seconds")
    description = models.TextField(blank=True, null=True)

    # API integration tracking
    auto_fetched = models.BooleanField(default=False, help_text="Was metadata fetched from API?")
    last_api_sync = models.DateTimeField(blank=True, null=True, help_text="Last time metadata was synced")

    # Other fields
    resource_file = models.FileField(upload_to='lesson_resources/', blank=True, null=True)
    is_preview = models.BooleanField(default=False, help_text="Free preview for non-enrolled students")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.title
    
    @property
    def effective_video_id(self):
        """Return the appropriate video ID based on platform"""
        if self.platform == 'youtube':
            return self.video_id or self.youtube_video_id
        elif self.platform == 'vimeo':
            return self.video_id or self.vimeo_video_id
        return self.video_id
    
    @property
    def effective_video_url(self):
        """Return the appropriate video URL based on platform"""
        if self.video_url:
            return self.video_url
        elif self.platform == 'youtube' and self.effective_video_id:
            return f"https://www.youtube.com/watch?v={self.effective_video_id}"
        elif self.platform == 'vimeo' and self.effective_video_id:
            return f"https://vimeo.com/{self.effective_video_id}"
        return self.youtube_url  # Fallback to legacy field
    
    @property
    def embed_url(self):
        """Return embeddable URL for the video"""
        video_id = self.effective_video_id
        if not video_id:
            return None
        
        if self.platform == 'youtube':
            return f"https://www.youtube.com/embed/{video_id}"
        elif self.platform == 'vimeo':
            return f"https://player.vimeo.com/video/{video_id}"
        
        return self.effective_video_url
    
    def sync_from_api(self):
        """Fetch and update metadata from video platform API"""
        from .services import VideoIntegrationService
        from django.utils import timezone

        url = self.video_url or self.youtube_url
        if not url:
            return False, "No video URL provided"

        metadata = VideoIntegrationService.fetch_video_metadata(url)

        if 'error' in metadata:
            return False, metadata['error']

        # Update fields with fetched metadata
        self.title = self.title or metadata.get('title', self.title)
        self.description = self.description or metadata.get('description', self.description)
        self.thumbnail_url = self.thumbnail_url or metadata.get('thumbnail_url', self.thumbnail_url)
        self.duration = self.duration or metadata.get('duration', self.duration)

        # Update platform-specific fields
        self.platform = metadata.get('platform', self.platform)
        self.video_id = metadata.get('video_id', self.video_id)
        if self.platform == 'youtube':
            self.youtube_video_id = self.youtube_video_id or self.video_id
        elif self.platform == 'vimeo':
            self.vimeo_video_id = self.vimeo_video_id or self.video_id

        # Update tracking fields
        self.auto_fetched = True
        self.last_api_sync = timezone.now()

        return True, "Metadata synced successfully"

    def get_first_module(self):
        """Helper method to get first module (for backward compatibility)"""
        first_link = self.module_links.select_related('module').first()
        return first_link.module if first_link else None

    def get_first_course(self):
        """Helper method to get first course via module (for backward compatibility)"""
        module = self.get_first_module()
        if module:
            first_course_link = module.course_links.select_related('course').first()
            return first_course_link.course if first_course_link else None
        return None

    @property
    def module(self):
        """Property for backward compatibility - returns first module"""
        if not hasattr(self, '_cached_module'):
            self._cached_module = self.get_first_module()
        return self._cached_module

    class Meta:
        db_table = 'video_lessons'
        ordering = ['title']

class Assignment(models.Model):
    """Reusable assignments that can be added to courses, modules, or video lessons"""
    # Many-to-many relationships at multiple levels
    courses = models.ManyToManyField('Course', through='CourseAssignment', related_name='course_assignments', blank=True)
    modules = models.ManyToManyField(Module, through='ModuleAssignment', related_name='module_assignments', blank=True)
    video_lessons = models.ManyToManyField('VideoLesson', through='VideoAssignment', related_name='video_assignments', blank=True)

    title = models.CharField(max_length=200)
    description = models.TextField(help_text="Assignment instructions and requirements")
    requirements = models.TextField(blank=True, null=True, help_text="Specific requirements (e.g., 'Create a Python script that...')")
    resources = models.TextField(blank=True, null=True, help_text="Additional resources or links")
    max_points = models.PositiveIntegerField(default=100, help_text="Maximum points for this assignment")
    passing_score = models.PositiveIntegerField(default=70, help_text="Minimum score to pass")
    due_days = models.PositiveIntegerField(default=7, help_text="Days from start to complete assignment")
    is_required = models.BooleanField(default=True, help_text="Required to proceed")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.title

    def get_first_course(self):
        """Get first directly linked course"""
        first_link = self.course_links.select_related('course').first()
        return first_link.course if first_link else None

    def get_first_module(self):
        """Helper method to get first module (for backward compatibility)"""
        first_link = self.module_links.select_related('module').first()
        return first_link.module if first_link else None

    def get_first_video(self):
        """Get first video lesson"""
        first_link = self.video_links.select_related('video_lesson').first()
        return first_link.video_lesson if first_link else None

    @property
    def module(self):
        """Property for backward compatibility - returns first module"""
        if not hasattr(self, '_cached_module'):
            self._cached_module = self.get_first_module()
        return self._cached_module

    class Meta:
        db_table = 'assignments'
        ordering = ['title']


class CourseAssignment(models.Model):
    """Through model for Course-Assignment relationship with ordering"""
    course = models.ForeignKey('Course', on_delete=models.CASCADE, related_name='assignment_links')
    assignment = models.ForeignKey(Assignment, on_delete=models.CASCADE, related_name='course_links')
    order = models.PositiveIntegerField(default=1, help_text="Order of assignment in this course")
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.course.title} - {self.assignment.title} (Order: {self.order})"

    class Meta:
        db_table = 'course_assignments'
        ordering = ['course', 'order']
        unique_together = ['course', 'assignment']


class ModuleAssignment(models.Model):
    """Through model for Module-Assignment relationship with ordering"""
    module = models.ForeignKey(Module, on_delete=models.CASCADE, related_name='assignment_links')
    assignment = models.ForeignKey(Assignment, on_delete=models.CASCADE, related_name='module_links')
    order = models.PositiveIntegerField(default=1, help_text="Order of assignment in this module")
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.module.title} - {self.assignment.title} (Order: {self.order})"

    class Meta:
        db_table = 'module_assignments'
        ordering = ['module', 'order']
        unique_together = ['module', 'assignment']


class VideoAssignment(models.Model):
    """Through model for VideoLesson-Assignment relationship with ordering"""
    video_lesson = models.ForeignKey('VideoLesson', on_delete=models.CASCADE, related_name='assignment_links')
    assignment = models.ForeignKey(Assignment, on_delete=models.CASCADE, related_name='video_links')
    order = models.PositiveIntegerField(default=1, help_text="Order of assignment for this video")
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.video_lesson.title} - {self.assignment.title} (Order: {self.order})"

    class Meta:
        db_table = 'video_assignments'
        ordering = ['video_lesson', 'order']
        unique_together = ['video_lesson', 'assignment']


class Quiz(models.Model):
    """Reusable quizzes that can be added to courses, modules, or video lessons"""
    # Many-to-many relationships at multiple levels
    courses = models.ManyToManyField('Course', through='CourseQuiz', related_name='course_quizzes', blank=True)
    modules = models.ManyToManyField(Module, through='ModuleQuiz', related_name='module_quizzes', blank=True)
    video_lessons = models.ManyToManyField('VideoLesson', through='VideoQuiz', related_name='video_quizzes', blank=True)

    title = models.CharField(max_length=200)
    description = models.TextField(help_text="Quiz instructions")
    time_limit = models.PositiveIntegerField(default=30, help_text="Time limit in minutes")
    max_attempts = models.PositiveIntegerField(default=3, help_text="Maximum attempts allowed")
    passing_score = models.PositiveIntegerField(default=70, help_text="Minimum score percentage to pass")
    is_required = models.BooleanField(default=True, help_text="Required to proceed")
    randomize_questions = models.BooleanField(default=True, help_text="Randomize question order")
    show_results_immediately = models.BooleanField(default=True, help_text="Show results after submission")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.title

    @property
    def total_questions(self):
        return self.questions.count()

    @property
    def total_points(self):
        return sum(q.points for q in self.questions.all())

    def get_first_course(self):
        """Get first directly linked course"""
        first_link = self.course_links.select_related('course').first()
        return first_link.course if first_link else None

    def get_first_module(self):
        """Helper method to get first module (for backward compatibility)"""
        first_link = self.module_links.select_related('module').first()
        return first_link.module if first_link else None

    def get_first_video(self):
        """Get first video lesson"""
        first_link = self.video_links.select_related('video_lesson').first()
        return first_link.video_lesson if first_link else None

    @property
    def module(self):
        """Property for backward compatibility - returns first module"""
        if not hasattr(self, '_cached_module'):
            self._cached_module = self.get_first_module()
        return self._cached_module

    class Meta:
        db_table = 'quizzes'
        ordering = ['title']


class CourseQuiz(models.Model):
    """Through model for Course-Quiz relationship with ordering"""
    course = models.ForeignKey('Course', on_delete=models.CASCADE, related_name='quiz_links')
    quiz = models.ForeignKey(Quiz, on_delete=models.CASCADE, related_name='course_links')
    order = models.PositiveIntegerField(default=1, help_text="Order of quiz in this course")
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.course.title} - {self.quiz.title} (Order: {self.order})"

    class Meta:
        db_table = 'course_quizzes'
        ordering = ['course', 'order']
        unique_together = ['course', 'quiz']


class ModuleQuiz(models.Model):
    """Through model for Module-Quiz relationship with ordering"""
    module = models.ForeignKey(Module, on_delete=models.CASCADE, related_name='quiz_links')
    quiz = models.ForeignKey(Quiz, on_delete=models.CASCADE, related_name='module_links')
    order = models.PositiveIntegerField(default=1, help_text="Order of quiz in this module")
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.module.title} - {self.quiz.title} (Order: {self.order})"

    class Meta:
        db_table = 'module_quizzes'
        ordering = ['module', 'order']
        unique_together = ['module', 'quiz']


class VideoQuiz(models.Model):
    """Through model for VideoLesson-Quiz relationship with ordering"""
    video_lesson = models.ForeignKey('VideoLesson', on_delete=models.CASCADE, related_name='quiz_links')
    quiz = models.ForeignKey(Quiz, on_delete=models.CASCADE, related_name='video_links')
    order = models.PositiveIntegerField(default=1, help_text="Order of quiz for this video")
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.video_lesson.title} - {self.quiz.title} (Order: {self.order})"

    class Meta:
        db_table = 'video_quizzes'
        ordering = ['video_lesson', 'order']
        unique_together = ['video_lesson', 'quiz']


class PDFNote(models.Model):
    """PDF notes/documents that can be added to courses, modules, or video lessons"""
    # Many-to-many relationships at multiple levels
    courses = models.ManyToManyField('Course', through='CoursePDF', related_name='course_pdfs', blank=True)
    modules = models.ManyToManyField(Module, through='ModulePDF', related_name='module_pdfs', blank=True)
    video_lessons = models.ManyToManyField('VideoLesson', through='VideoPDF', related_name='video_pdfs', blank=True)

    title = models.CharField(max_length=200)
    description = models.TextField(blank=True, null=True, help_text="Description of the PDF content")
    pdf_file = models.FileField(upload_to='course_pdfs/', help_text="Upload PDF file")
    file_size = models.PositiveIntegerField(blank=True, null=True, help_text="File size in bytes")
    page_count = models.PositiveIntegerField(blank=True, null=True, help_text="Number of pages")
    is_downloadable = models.BooleanField(default=True, help_text="Allow students to download")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.title

    def get_first_course(self):
        """Get first directly linked course"""
        first_link = self.course_links.select_related('course').first()
        return first_link.course if first_link else None

    def get_first_module(self):
        """Get first module"""
        first_link = self.module_links.select_related('module').first()
        return first_link.module if first_link else None

    def get_first_video(self):
        """Get first video lesson"""
        first_link = self.video_links.select_related('video_lesson').first()
        return first_link.video_lesson if first_link else None

    class Meta:
        db_table = 'pdf_notes'
        ordering = ['title']


class CoursePDF(models.Model):
    """Through model for Course-PDFNote relationship with ordering"""
    course = models.ForeignKey('Course', on_delete=models.CASCADE, related_name='pdf_links')
    pdf_note = models.ForeignKey(PDFNote, on_delete=models.CASCADE, related_name='course_links')
    order = models.PositiveIntegerField(default=1, help_text="Order of PDF in this course")
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.course.title} - {self.pdf_note.title} (Order: {self.order})"

    class Meta:
        db_table = 'course_pdfs'
        ordering = ['course', 'order']
        unique_together = ['course', 'pdf_note']


class ModulePDF(models.Model):
    """Through model for Module-PDFNote relationship with ordering"""
    module = models.ForeignKey(Module, on_delete=models.CASCADE, related_name='pdf_links')
    pdf_note = models.ForeignKey(PDFNote, on_delete=models.CASCADE, related_name='module_links')
    order = models.PositiveIntegerField(default=1, help_text="Order of PDF in this module")
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.module.title} - {self.pdf_note.title} (Order: {self.order})"

    class Meta:
        db_table = 'module_pdfs'
        ordering = ['module', 'order']
        unique_together = ['module', 'pdf_note']


class VideoPDF(models.Model):
    """Through model for VideoLesson-PDFNote relationship with ordering"""
    video_lesson = models.ForeignKey('VideoLesson', on_delete=models.CASCADE, related_name='pdf_links')
    pdf_note = models.ForeignKey(PDFNote, on_delete=models.CASCADE, related_name='video_links')
    order = models.PositiveIntegerField(default=1, help_text="Order of PDF for this video")
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.video_lesson.title} - {self.pdf_note.title} (Order: {self.order})"

    class Meta:
        db_table = 'video_pdfs'
        ordering = ['video_lesson', 'order']
        unique_together = ['video_lesson', 'pdf_note']


class QuizQuestion(models.Model):
    """Individual questions within a quiz"""
    QUESTION_TYPES = [
        ('multiple_choice', 'Multiple Choice'),
        ('true_false', 'True/False'),
        ('short_answer', 'Short Answer'),
        ('essay', 'Essay'),
    ]

    quiz = models.ForeignKey(Quiz, on_delete=models.CASCADE, related_name='questions')
    question_text = models.TextField()
    question_type = models.CharField(max_length=20, choices=QUESTION_TYPES, default='multiple_choice')
    points = models.PositiveIntegerField(default=1)
    explanation = models.TextField(blank=True, null=True, help_text="Explanation shown after answering")
    order = models.PositiveIntegerField(default=1)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.quiz.title} - Q{self.order}"

    class Meta:
        db_table = 'quiz_questions'
        ordering = ['order']
        unique_together = ['quiz', 'order']


class QuizChoice(models.Model):
    """Choices for multiple choice questions"""
    question = models.ForeignKey(QuizQuestion, on_delete=models.CASCADE, related_name='choices')
    choice_text = models.CharField(max_length=500)
    is_correct = models.BooleanField(default=False)
    order = models.PositiveIntegerField(default=1)
    
    def __str__(self):
        return f"{self.question} - {self.choice_text[:50]}"
    
    class Meta:
        db_table = 'quiz_choices'
        ordering = ['order']


class AssignmentSubmission(models.Model):
    """Student submissions for assignments"""
    SUBMISSION_STATUS = [
        ('draft', 'Draft'),
        ('submitted', 'Submitted'),
        ('under_review', 'Under Review'),
        ('graded', 'Graded'),
        ('returned', 'Returned for Revision'),
    ]
    
    assignment = models.ForeignKey(Assignment, on_delete=models.CASCADE, related_name='submissions')
    student = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='assignment_submissions')
    github_url = models.URLField(help_text="URL to submission (GitHub, GitLab, Figma, CodePen, Repl.it, CodeSandbox, Vercel, Netlify, or any public URL)")
    submission_notes = models.TextField(blank=True, null=True, help_text="Student's notes about the submission")
    status = models.CharField(max_length=20, choices=SUBMISSION_STATUS, default='draft')
    
    # Grading fields
    score = models.PositiveIntegerField(null=True, blank=True, help_text="Score out of max_points")
    grade_comments = models.TextField(blank=True, null=True, help_text="Instructor feedback")
    graded_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='graded_assignments')
    graded_at = models.DateTimeField(null=True, blank=True)
    
    # Timestamps
    submitted_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"{self.student.name} - {self.assignment.title}"
    
    @property
    def is_passed(self):
        if self.score is None:
            return False
        return self.score >= self.assignment.passing_score
    
    @property
    def score_percentage(self):
        if self.score is None:
            return 0
        return (self.score / self.assignment.max_points) * 100
    
    def submit(self):
        """Mark submission as submitted"""
        from django.utils import timezone
        self.status = 'submitted'
        self.submitted_at = timezone.now()
        self.save()
    
    def grade(self, score, comments, graded_by):
        """Grade the submission"""
        from django.utils import timezone
        self.score = score
        self.grade_comments = comments
        self.graded_by = graded_by
        self.graded_at = timezone.now()
        self.status = 'graded'
        self.save()
    
    class Meta:
        db_table = 'assignment_submissions'
        unique_together = ['assignment', 'student']


class QuizAttempt(models.Model):
    """Student attempts at quizzes"""
    quiz = models.ForeignKey(Quiz, on_delete=models.CASCADE, related_name='attempts')
    student = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='quiz_attempts')
    attempt_number = models.PositiveIntegerField(default=1)
    score = models.PositiveIntegerField(default=0)
    total_points = models.PositiveIntegerField(default=0)
    time_taken = models.PositiveIntegerField(null=True, blank=True, help_text="Time taken in seconds")
    completed = models.BooleanField(default=False)
    started_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    
    def __str__(self):
        return f"{self.student.name} - {self.quiz.title} (Attempt {self.attempt_number})"
    
    @property
    def score_percentage(self):
        if self.total_points == 0:
            return 0
        return (self.score / self.total_points) * 100
    
    @property
    def is_passed(self):
        return self.score_percentage >= self.quiz.passing_score
    
    @property
    def correct_answers(self):
        """Count of correct answers"""
        return self.answers.filter(is_correct=True).count()
    
    @property
    def total_questions(self):
        """Total number of questions in the quiz"""
        return self.quiz.questions.count()
    
    @property
    def accuracy(self):
        """Accuracy percentage based on correct answers"""
        if self.total_questions == 0:
            return 0
        return (self.correct_answers / self.total_questions) * 100
    
    @property
    def time_taken_minutes(self):
        """Time taken in minutes (formatted)"""
        if self.time_taken is None:
            return None
        minutes = self.time_taken // 60
        seconds = self.time_taken % 60
        if minutes > 0:
            return f"{minutes}m {seconds}s"
        else:
            return f"{seconds}s"
    
    @property
    def status(self):
        """Get attempt status"""
        if not self.completed:
            return 'in_progress'
        elif self.completed:
            return 'completed'
        else:
            return 'timed_out'
    
    def complete(self):
        """Mark attempt as completed"""
        from django.utils import timezone
        self.completed = True
        self.completed_at = timezone.now()
        self.save()
    
    class Meta:
        db_table = 'quiz_attempts'
        unique_together = ['quiz', 'student', 'attempt_number']


class QuizAnswer(models.Model):
    """Student answers to quiz questions"""
    attempt = models.ForeignKey(QuizAttempt, on_delete=models.CASCADE, related_name='answers')
    question = models.ForeignKey(QuizQuestion, on_delete=models.CASCADE)
    selected_choice = models.ForeignKey(QuizChoice, on_delete=models.CASCADE, null=True, blank=True)
    text_answer = models.TextField(blank=True, null=True, help_text="For short answer/essay questions")
    is_correct = models.BooleanField(default=False)
    points_earned = models.PositiveIntegerField(default=0)
    
    def __str__(self):
        return f"{self.attempt.student.name} - {self.question}"
    
    class Meta:
        db_table = 'quiz_answers'
        unique_together = ['attempt', 'question']


class ModuleProgress(models.Model):
    """Track student progress through modules"""
    student = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='module_progress')
    module = models.ForeignKey(Module, on_delete=models.CASCADE, related_name='student_progress')
    
    # Progress tracking
    videos_completed = models.PositiveIntegerField(default=0)
    assignments_completed = models.PositiveIntegerField(default=0)
    quizzes_passed = models.PositiveIntegerField(default=0)
    
    # Status
    is_unlocked = models.BooleanField(default=False, help_text="Can student access this module")
    is_completed = models.BooleanField(default=False, help_text="Has student completed all requirements")
    completion_percentage = models.DecimalField(max_digits=5, decimal_places=2, default=0.0)
    
    # Timestamps
    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"{self.student.name} - {self.module.title}"
    
    @property
    def status(self):
        """Get current progress status"""
        if not self.is_unlocked:
            return 'blocked'
        elif self.is_completed:
            return 'completed'
        elif self.started_at:
            return 'in_progress'
        else:
            return 'not_started'
    
    def check_completion(self):
        """Check if module is completed and update status"""
        # Check video completion - use the through table relationship
        total_videos = self.module.video_links.count()

        # Count completed videos for this module (need to go through the through table)
        completed_video_ids = self.student.progress.filter(
            completed=True
        ).values_list('video_lesson_id', flat=True)

        module_video_ids = self.module.video_links.values_list('video_lesson_id', flat=True)
        completed_videos = len(set(completed_video_ids) & set(module_video_ids))

        # Check assignment completion - use the through table relationship
        assignment_links = self.module.assignment_links.select_related('assignment')
        required_assignments = [link.assignment for link in assignment_links if link.assignment.is_required]
        passed_assignments = 0
        for assignment in required_assignments:
            try:
                submission = assignment.submissions.get(student=self.student)
                if submission.is_passed:
                    passed_assignments += 1
            except AssignmentSubmission.DoesNotExist:
                pass

        # Check quiz completion - use the through table relationship
        quiz_links = self.module.quiz_links.select_related('quiz')
        required_quizzes = [link.quiz for link in quiz_links if link.quiz.is_required]
        passed_quizzes = 0
        for quiz in required_quizzes:
            best_attempt = quiz.attempts.filter(student=self.student, completed=True).order_by('-score').first()
            if best_attempt and best_attempt.is_passed:
                passed_quizzes += 1
        
        # Update progress
        self.videos_completed = completed_videos
        self.assignments_completed = passed_assignments
        self.quizzes_passed = passed_quizzes

        # Calculate completion percentage
        total_requirements = total_videos + len(required_assignments) + len(required_quizzes)
        completed_requirements = completed_videos + passed_assignments + passed_quizzes

        if total_requirements > 0:
            self.completion_percentage = (completed_requirements / total_requirements) * 100
        else:
            self.completion_percentage = 100

        # Check if completed
        all_videos_done = (total_videos == 0) or (completed_videos == total_videos)
        all_assignments_done = (len(required_assignments) == 0) or (passed_assignments == len(required_assignments))
        all_quizzes_done = (len(required_quizzes) == 0) or (passed_quizzes == len(required_quizzes))
        
        was_completed = self.is_completed
        self.is_completed = all_videos_done and all_assignments_done and all_quizzes_done
        
        if self.is_completed and not was_completed:
            from django.utils import timezone
            self.completed_at = timezone.now()
            
            # Sequential unlocking disabled - all modules accessible
        
        self.save()
        return self.is_completed
    
    def _unlock_next_module(self):
        """Sequential unlocking disabled - method kept for compatibility"""
        pass
    
    class Meta:
        db_table = 'module_progress'
        unique_together = ['student', 'module']


class StudentProgress(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='progress')
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name='student_progress')
    video_lesson = models.ForeignKey(VideoLesson, on_delete=models.CASCADE, related_name='student_progress')
    completed_percentage = models.DecimalField(max_digits=5, decimal_places=2, default=0.0)
    last_watched_at = models.DateTimeField(auto_now=True)
    completed = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"{self.user.name} - {self.video_lesson.title} ({self.completed_percentage}%)"
    
    class Meta:
        db_table = 'student_progress'
        unique_together = ['user', 'video_lesson']


class StudentAnalytics(models.Model):
    """Comprehensive analytics for student performance and mentoring"""
    student = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='analytics')
    
    # Engagement Metrics
    total_login_days = models.PositiveIntegerField(default=0)
    last_login = models.DateTimeField(null=True, blank=True)
    avg_daily_study_time = models.DurationField(default=timezone.timedelta(0))
    total_videos_watched = models.PositiveIntegerField(default=0)
    total_assignments_submitted = models.PositiveIntegerField(default=0)
    total_quizzes_attempted = models.PositiveIntegerField(default=0)
    
    # Performance Metrics
    avg_quiz_score = models.DecimalField(max_digits=5, decimal_places=2, default=0.0)
    avg_assignment_score = models.DecimalField(max_digits=5, decimal_places=2, default=0.0)
    courses_completed = models.PositiveIntegerField(default=0)
    modules_completed = models.PositiveIntegerField(default=0)
    
    # Risk Assessment
    RISK_LEVELS = [
        ('low', 'Low Risk'),
        ('medium', 'Medium Risk'),
        ('high', 'High Risk'),
        ('critical', 'Critical Risk'),
    ]
    risk_level = models.CharField(max_length=10, choices=RISK_LEVELS, default='low')
    risk_score = models.DecimalField(max_digits=5, decimal_places=2, default=0.0, help_text="0-100 risk score")
    needs_mentoring = models.BooleanField(default=False)
    
    # Mentoring Support
    assigned_mentor = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='mentee_analytics')
    last_mentor_contact = models.DateTimeField(null=True, blank=True)
    mentoring_notes = models.TextField(blank=True, null=True)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"Analytics: {self.student.name}"
    
    def calculate_risk_score(self):
        """Calculate risk score based on multiple factors"""
        from django.utils import timezone
        from datetime import timedelta
        
        score = 0
        
        # Inactivity risk (40% weight)
        if self.last_login:
            days_inactive = (timezone.now() - self.last_login).days
            if days_inactive > 14:
                score += 40
            elif days_inactive > 7:
                score += 25
            elif days_inactive > 3:
                score += 10
        else:
            score += 40
        
        # Performance risk (35% weight)
        if self.avg_quiz_score < 50:
            score += 20
        elif self.avg_quiz_score < 70:
            score += 10
        
        if self.avg_assignment_score < 50:
            score += 15
        elif self.avg_assignment_score < 70:
            score += 8
        
        # Engagement risk (25% weight)
        if self.total_videos_watched == 0 and self.student.enrollments.filter(active=True).exists():
            score += 15
        
        if self.avg_daily_study_time.total_seconds() < 1800:  # Less than 30 mins
            score += 10
        
        self.risk_score = min(score, 100)  # Cap at 100
        
        # Set risk level
        if self.risk_score >= 80:
            self.risk_level = 'critical'
            self.needs_mentoring = True
        elif self.risk_score >= 60:
            self.risk_level = 'high'
            self.needs_mentoring = True
        elif self.risk_score >= 40:
            self.risk_level = 'medium'
        else:
            self.risk_level = 'low'
            
        self.save()
        return self.risk_score
    
    def update_metrics(self):
        """Update all metrics with current data from database"""
        from django.db.models import Avg
        
        # Update basic counts
        self.total_videos_watched = StudentProgress.objects.filter(
            user=self.student, 
            completed=True
        ).count()
        
        self.total_assignments_submitted = AssignmentSubmission.objects.filter(
            student=self.student
        ).exclude(status='draft').count()
        
        self.total_quizzes_attempted = QuizAttempt.objects.filter(
            student=self.student,
            completed=True
        ).count()
        
        # Update performance metrics
        # Calculate average quiz score percentage using database fields
        from django.db.models import F, FloatField
        from django.db.models.functions import Cast

        quiz_attempts = QuizAttempt.objects.filter(
            student=self.student,
            completed=True
        ).exclude(total_points=0)  # Avoid division by zero

        if quiz_attempts.exists():
            # Calculate percentage in database: (score / total_points) * 100
            quiz_avg = quiz_attempts.aggregate(
                avg_score=Avg(
                    Cast(F('score'), FloatField()) * 100.0 / Cast(F('total_points'), FloatField())
                )
            )['avg_score']
            self.avg_quiz_score = quiz_avg or 0
        else:
            self.avg_quiz_score = 0
        
        # Calculate average assignment score percentage
        assignment_submissions = AssignmentSubmission.objects.filter(
            student=self.student
        ).exclude(status='draft').exclude(score__isnull=True).select_related('assignment')

        if assignment_submissions.exists():
            # Calculate percentage in database: (score / max_points) * 100
            assignment_avg = assignment_submissions.aggregate(
                avg_grade=Avg(
                    Cast(F('score'), FloatField()) * 100.0 / Cast(F('assignment__max_points'), FloatField())
                )
            )['avg_grade']
            self.avg_assignment_score = assignment_avg or 0
        else:
            self.avg_assignment_score = 0
        
        # Update login data
        self.last_login = self.student.last_login
        
        # Calculate completed modules
        # Get completed videos
        completed_video_ids = StudentProgress.objects.filter(
            user=self.student,
            completed=True
        ).values_list('video_lesson_id', flat=True)

        # Get modules that contain these videos through ModuleVideo
        from apps.courses.models import ModuleVideo
        completed_module_ids = ModuleVideo.objects.filter(
            video_lesson_id__in=completed_video_ids
        ).values_list('module_id', flat=True).distinct()

        self.modules_completed = len(set(completed_module_ids))
        
        # Recalculate risk score with updated data
        self.calculate_risk_score()
    
    class Meta:
        db_table = 'student_analytics'
        verbose_name_plural = 'Student Analytics'


class ProgressAlert(models.Model):
    """Alerts for mentors about at-risk students"""
    ALERT_TYPES = [
        ('inactive', 'Student Inactive'),
        ('poor_performance', 'Poor Performance'),
        ('no_submission', 'No Assignment Submissions'),
        ('quiz_failure', 'Multiple Quiz Failures'),
        ('course_stalled', 'Course Progress Stalled'),
    ]
    
    ALERT_PRIORITY = [
        ('low', 'Low'),
        ('medium', 'Medium'),  
        ('high', 'High'),
        ('urgent', 'Urgent'),
    ]
    
    student = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='alerts')
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name='alerts')
    alert_type = models.CharField(max_length=20, choices=ALERT_TYPES)
    priority = models.CharField(max_length=10, choices=ALERT_PRIORITY)
    title = models.CharField(max_length=200)
    description = models.TextField()
    
    # Status
    is_resolved = models.BooleanField(default=False)
    resolved_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='resolved_alerts')
    resolved_at = models.DateTimeField(null=True, blank=True)
    resolution_notes = models.TextField(blank=True, null=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"Alert: {self.student.name} - {self.title}"
    
    def resolve(self, resolved_by, notes=""):
        """Mark alert as resolved"""
        from django.utils import timezone
        self.is_resolved = True
        self.resolved_by = resolved_by
        self.resolved_at = timezone.now()
        self.resolution_notes = notes
        self.save()
    
    class Meta:
        db_table = 'progress_alerts'
        ordering = ['-created_at']


class MentorSession(models.Model):
    """Track mentoring sessions with students"""
    SESSION_TYPES = [
        ('video_call', 'Video Call'),
        ('phone_call', 'Phone Call'),
        ('email', 'Email Support'),
        ('chat', 'Chat Session'),
        ('in_person', 'In Person'),
    ]
    
    mentor = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='mentor_sessions')
    student = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='mentoring_sessions')
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name='mentoring_sessions', null=True, blank=True)
    
    session_type = models.CharField(max_length=15, choices=SESSION_TYPES)
    duration_minutes = models.PositiveIntegerField(help_text="Session duration in minutes")
    
    # Content
    topics_discussed = models.TextField(help_text="What was discussed in the session")
    action_items = models.TextField(blank=True, null=True, help_text="Action items for student")
    follow_up_required = models.BooleanField(default=False)
    follow_up_date = models.DateField(null=True, blank=True)
    
    # Ratings
    student_satisfaction = models.PositiveIntegerField(null=True, blank=True, help_text="1-5 rating from student")
    mentor_notes = models.TextField(blank=True, null=True)
    
    session_date = models.DateTimeField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"Session: {self.mentor.name} -> {self.student.name} ({self.session_date.date()})"

    class Meta:
        db_table = 'mentor_sessions'
        ordering = ['-session_date']


class Certificate(models.Model):
    """
    Certificates issued to students upon course completion.
    Supports PDF generation and verification.
    """
    CERTIFICATE_TYPES = [
        ('completion', 'Course Completion'),
        ('excellence', 'Excellence Award'),
        ('participation', 'Participation'),
    ]

    student = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='certificates'
    )
    course = models.ForeignKey(
        Course,
        on_delete=models.CASCADE,
        related_name='certificates'
    )
    enrollment = models.OneToOneField(
        'payments.Enrollment',
        on_delete=models.CASCADE,
        related_name='certificate',
        null=True,
        blank=True
    )

    # Certificate details
    certificate_number = models.CharField(max_length=50, unique=True)
    certificate_type = models.CharField(
        max_length=20,
        choices=CERTIFICATE_TYPES,
        default='completion'
    )
    title = models.CharField(
        max_length=200,
        help_text="Title displayed on certificate (e.g., 'Certificate of Completion')"
    )
    description = models.TextField(
        blank=True,
        null=True,
        help_text="Additional text to display on certificate"
    )

    # Completion info
    completion_date = models.DateField(help_text="Date when course was completed")
    issue_date = models.DateField(auto_now_add=True)

    # Score/Grade (optional)
    final_score = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Final score percentage (if applicable)"
    )
    grade = models.CharField(
        max_length=10,
        blank=True,
        null=True,
        help_text="Grade (e.g., A+, A, B+, etc.)"
    )

    # Verification
    verification_code = models.CharField(
        max_length=100,
        unique=True,
        help_text="Unique code for certificate verification"
    )
    verification_url = models.URLField(
        blank=True,
        null=True,
        help_text="Full URL for certificate verification"
    )

    # PDF Storage
    pdf_file = models.FileField(
        upload_to='certificates/',
        blank=True,
        null=True,
        help_text="Generated PDF certificate"
    )

    # Status
    is_revoked = models.BooleanField(
        default=False,
        help_text="Set to True if certificate is revoked"
    )
    revoked_reason = models.TextField(blank=True, null=True)
    revoked_at = models.DateTimeField(null=True, blank=True)

    # Signature
    signed_by = models.CharField(
        max_length=200,
        blank=True,
        null=True,
        help_text="Name of person who signed the certificate"
    )
    signed_by_title = models.CharField(
        max_length=200,
        blank=True,
        null=True,
        help_text="Title of person who signed (e.g., 'Director of Training')"
    )

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'certificates'
        ordering = ['-issue_date']
        # Note: unique_together removed - validation in save() ensures only one ACTIVE certificate per student-course

    def __str__(self):
        return f"{self.certificate_number} - {self.student.name} - {self.course.title}"

    def save(self, *args, **kwargs):
        # Check if an active certificate already exists for this student-course combination
        if not self.pk:  # Only check on creation
            existing_active = Certificate.objects.filter(
                student=self.student,
                course=self.course,
                is_revoked=False
            ).exists()
            if existing_active:
                raise ValidationError(
                    f'An active certificate already exists for this student in this course. '
                    f'Please revoke the existing certificate before issuing a new one.'
                )

        if not self.certificate_number:
            self.certificate_number = self.generate_certificate_number()
        if not self.verification_code:
            self.verification_code = self.generate_verification_code()
        super().save(*args, **kwargs)

    @staticmethod
    def generate_certificate_number():
        """Generate a unique certificate number like LMS-2025-000001"""
        import uuid
        from datetime import date
        year = date.today().year
        unique_part = str(uuid.uuid4().hex)[:6].upper()
        # Get count of certificates this year
        year_count = Certificate.objects.filter(
            created_at__year=year
        ).count() + 1
        return f"LMS-{year}-{year_count:06d}"

    @staticmethod
    def generate_verification_code():
        """Generate a unique verification code"""
        import uuid
        import hashlib
        unique_string = str(uuid.uuid4())
        return hashlib.sha256(unique_string.encode()).hexdigest()[:32].upper()

    def revoke(self, reason=''):
        """Revoke this certificate"""
        self.is_revoked = True
        self.revoked_reason = reason
        self.revoked_at = timezone.now()
        self.save()

    @property
    def is_valid(self):
        """Check if certificate is valid (not revoked)"""
        return not self.is_revoked

    @property
    def grade_display(self):
        """Get grade based on final score if not manually set"""
        if self.grade:
            return self.grade
        if self.final_score is None:
            return None
        score = float(self.final_score)
        if score >= 90:
            return 'A+'
        elif score >= 85:
            return 'A'
        elif score >= 80:
            return 'B+'
        elif score >= 75:
            return 'B'
        elif score >= 70:
            return 'C+'
        elif score >= 65:
            return 'C'
        elif score >= 60:
            return 'D'
        else:
            return 'F'


class DailyStreak(models.Model):
    """Track daily learning streaks for students"""
    student = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='daily_streak'
    )

    # Streak data
    current_streak = models.PositiveIntegerField(default=0, help_text="Current consecutive days streak")
    longest_streak = models.PositiveIntegerField(default=0, help_text="Longest streak ever achieved")
    total_active_days = models.PositiveIntegerField(default=0, help_text="Total days with learning activity")

    # Streak tracking
    streak_start_date = models.DateField(null=True, blank=True, help_text="Start date of current streak")
    last_activity_date = models.DateField(null=True, blank=True, help_text="Last date with activity")

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'daily_streaks'
        verbose_name = 'Daily Streak'
        verbose_name_plural = 'Daily Streaks'

    def __str__(self):
        return f"{self.student.name} - {self.current_streak} days streak"

    def record_activity(self):
        """Record activity for today and update streak"""
        from datetime import timedelta
        today = timezone.now().date()

        # If already recorded today, just return
        if self.last_activity_date == today:
            return self.current_streak

        # Check if streak continues (yesterday or today is first day)
        if self.last_activity_date is None:
            # First activity ever
            self.current_streak = 1
            self.streak_start_date = today
            self.total_active_days = 1
        elif self.last_activity_date == today - timedelta(days=1):
            # Streak continues (yesterday was active)
            self.current_streak += 1
        else:
            # Streak broken - start new streak
            self.current_streak = 1
            self.streak_start_date = today
            self.total_active_days += 1

        # Update longest streak if current is higher
        if self.current_streak > self.longest_streak:
            self.longest_streak = self.current_streak

        self.last_activity_date = today
        self.save()

        # Record in daily activity log
        DailyActivity.objects.get_or_create(
            student=self.student,
            activity_date=today,
            defaults={'activities_count': 1}
        )

        return self.current_streak

    def check_streak_status(self):
        """Check if streak is still valid (called on login or API access)"""
        from datetime import timedelta
        today = timezone.now().date()

        if self.last_activity_date is None:
            return 0

        days_since_activity = (today - self.last_activity_date).days

        if days_since_activity > 1:
            # Streak is broken (more than 1 day gap)
            self.current_streak = 0
            self.streak_start_date = None
            self.save()

        return self.current_streak

    @classmethod
    def get_or_create_for_user(cls, user):
        """Get or create streak record for user"""
        streak, created = cls.objects.get_or_create(student=user)
        if not created:
            streak.check_streak_status()
        return streak


class DailyActivity(models.Model):
    """Log daily activity for streak tracking and analytics"""
    student = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='daily_activities'
    )
    activity_date = models.DateField()

    # Activity counts
    activities_count = models.PositiveIntegerField(default=0, help_text="Total activities on this day")
    videos_watched = models.PositiveIntegerField(default=0)
    quizzes_attempted = models.PositiveIntegerField(default=0)
    assignments_submitted = models.PositiveIntegerField(default=0)
    learning_minutes = models.PositiveIntegerField(default=0, help_text="Total learning time in minutes")

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'daily_activities'
        unique_together = ['student', 'activity_date']
        ordering = ['-activity_date']
        verbose_name = 'Daily Activity'
        verbose_name_plural = 'Daily Activities'

    def __str__(self):
        return f"{self.student.name} - {self.activity_date}"

    @classmethod
    def record_activity(cls, user, activity_type='general', minutes=0):
        """Record an activity and update streak"""
        today = timezone.now().date()

        # Get or create today's activity record
        activity, created = cls.objects.get_or_create(
            student=user,
            activity_date=today,
            defaults={'activities_count': 0}
        )

        # Update activity counts
        activity.activities_count += 1
        activity.learning_minutes += minutes

        if activity_type == 'video':
            activity.videos_watched += 1
        elif activity_type == 'quiz':
            activity.quizzes_attempted += 1
        elif activity_type == 'assignment':
            activity.assignments_submitted += 1

        activity.save()

        # Update streak
        streak = DailyStreak.get_or_create_for_user(user)
        streak.record_activity()

        return activity
