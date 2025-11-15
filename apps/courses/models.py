from django.db import models
from django.conf import settings
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
    allow_public_enrollment = models.BooleanField(default=True, help_text="Allow students to enroll via app/API. If False, only admin can enroll students.")
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
