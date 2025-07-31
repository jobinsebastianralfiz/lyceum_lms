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
