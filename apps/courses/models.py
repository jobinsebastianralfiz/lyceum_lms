from django.db import models
from django.conf import settings

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
    title = models.CharField(max_length=200)
    description = models.TextField()
    category = models.ForeignKey(Category, on_delete=models.CASCADE, related_name='courses')
    price = models.DecimalField(max_digits=10, decimal_places=2, default=0.00, help_text="Price excluding tax (0 for free courses)")
    tax_rate = models.DecimalField(max_digits=5, decimal_places=2, default=18.0, help_text="Tax rate in percentage")
    is_free = models.BooleanField(default=False, help_text="Mark as true for free courses")
    thumbnail = models.ImageField(upload_to='course_thumbnails/', blank=True, null=True)
    preview_video = models.URLField(blank=True, null=True, help_text="YouTube video URL for preview")
    is_published = models.BooleanField(default=False)
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

class Module(models.Model):
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name='modules')
    title = models.CharField(max_length=200)
    order = models.PositiveIntegerField(default=1, help_text="Order of module in the course")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"{self.course.title} - {self.title}"
    
    class Meta:
        db_table = 'modules'
        ordering = ['order']

class VideoLesson(models.Model):
    module = models.ForeignKey(Module, on_delete=models.CASCADE, related_name='video_lessons')
    title = models.CharField(max_length=200)
    youtube_video_id = models.CharField(max_length=20, blank=True, null=True, help_text="YouTube video ID (optional)")
    youtube_url = models.URLField(blank=True, null=True, help_text="Full YouTube URL (optional)")
    thumbnail_url = models.URLField(blank=True, null=True)
    duration = models.PositiveIntegerField(default=0, help_text="Duration in seconds")
    description = models.TextField(blank=True, null=True)
    resource_file = models.FileField(upload_to='lesson_resources/', blank=True, null=True)
    order = models.PositiveIntegerField(default=1, help_text="Order of lesson in the module")
    is_preview = models.BooleanField(default=False, help_text="Free preview for non-enrolled students")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"{self.module.title} - {self.title}"
    
    class Meta:
        db_table = 'video_lessons'
        ordering = ['order']

class Assignment(models.Model):
    """Assignments that students must complete to progress"""
    module = models.ForeignKey(Module, on_delete=models.CASCADE, related_name='assignments')
    title = models.CharField(max_length=200)
    description = models.TextField(help_text="Assignment instructions and requirements")
    requirements = models.TextField(blank=True, null=True, help_text="Specific requirements (e.g., 'Create a Python script that...')")
    resources = models.TextField(blank=True, null=True, help_text="Additional resources or links")
    max_points = models.PositiveIntegerField(default=100, help_text="Maximum points for this assignment")
    passing_score = models.PositiveIntegerField(default=70, help_text="Minimum score to pass")
    due_days = models.PositiveIntegerField(default=7, help_text="Days from module start to complete assignment")
    is_required = models.BooleanField(default=True, help_text="Required to proceed to next module")
    order = models.PositiveIntegerField(default=1, help_text="Order within the module")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"{self.module.title} - {self.title}"
    
    class Meta:
        db_table = 'assignments'
        ordering = ['order']
        unique_together = ['module', 'order']


class Quiz(models.Model):
    """Quizzes that students must complete to progress"""
    module = models.ForeignKey(Module, on_delete=models.CASCADE, related_name='quizzes')
    title = models.CharField(max_length=200)
    description = models.TextField(help_text="Quiz instructions")
    time_limit = models.PositiveIntegerField(default=30, help_text="Time limit in minutes")
    max_attempts = models.PositiveIntegerField(default=3, help_text="Maximum attempts allowed")
    passing_score = models.PositiveIntegerField(default=70, help_text="Minimum score percentage to pass")
    is_required = models.BooleanField(default=True, help_text="Required to proceed to next module")
    randomize_questions = models.BooleanField(default=True, help_text="Randomize question order")
    show_results_immediately = models.BooleanField(default=True, help_text="Show results after submission")
    order = models.PositiveIntegerField(default=1, help_text="Order within the module")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"{self.module.title} - {self.title}"
    
    @property
    def total_questions(self):
        return self.questions.count()
    
    @property
    def total_points(self):
        return sum(q.points for q in self.questions.all())
    
    class Meta:
        db_table = 'quizzes'
        ordering = ['order']
        unique_together = ['module', 'order']


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
    github_url = models.URLField(help_text="GitHub repository or file URL")
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
    
    def check_completion(self):
        """Check if module is completed and update status"""
        # Check video completion
        total_videos = self.module.video_lessons.count()
        completed_videos = self.student.progress.filter(
            video_lesson__module=self.module, 
            completed=True
        ).count()
        
        # Check assignment completion
        required_assignments = self.module.assignments.filter(is_required=True)
        passed_assignments = 0
        for assignment in required_assignments:
            try:
                submission = assignment.submissions.get(student=self.student)
                if submission.is_passed:
                    passed_assignments += 1
            except AssignmentSubmission.DoesNotExist:
                pass
        
        # Check quiz completion
        required_quizzes = self.module.quizzes.filter(is_required=True)
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
        total_requirements = total_videos + required_assignments.count() + required_quizzes.count()
        completed_requirements = completed_videos + passed_assignments + passed_quizzes
        
        if total_requirements > 0:
            self.completion_percentage = (completed_requirements / total_requirements) * 100
        else:
            self.completion_percentage = 100
        
        # Check if completed
        all_videos_done = (total_videos == 0) or (completed_videos == total_videos)
        all_assignments_done = (required_assignments.count() == 0) or (passed_assignments == required_assignments.count())
        all_quizzes_done = (required_quizzes.count() == 0) or (passed_quizzes == required_quizzes.count())
        
        was_completed = self.is_completed
        self.is_completed = all_videos_done and all_assignments_done and all_quizzes_done
        
        if self.is_completed and not was_completed:
            from django.utils import timezone
            self.completed_at = timezone.now()
            
            # Unlock next module
            self._unlock_next_module()
        
        self.save()
        return self.is_completed
    
    def _unlock_next_module(self):
        """Unlock the next module in sequence"""
        next_module = Module.objects.filter(
            course=self.module.course,
            order__gt=self.module.order
        ).order_by('order').first()
        
        if next_module:
            next_progress, created = ModuleProgress.objects.get_or_create(
                student=self.student,
                module=next_module,
                defaults={'is_unlocked': True}
            )
            if not created and not next_progress.is_unlocked:
                next_progress.is_unlocked = True
                next_progress.save()
    
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
