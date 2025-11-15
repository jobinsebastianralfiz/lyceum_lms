from django.contrib import admin
from django import forms
from .models import (
    Category, Course, Module, VideoLesson, StudentProgress,
    Assignment, Quiz, QuizQuestion, QuizChoice, AssignmentSubmission,
    QuizAttempt, QuizAnswer, ModuleProgress, CourseModule, ModuleVideo,
    ModuleAssignment, ModuleQuiz, PDFNote,
    CourseAssignment, CourseQuiz, CoursePDF,
    VideoAssignment, VideoQuiz, VideoPDF, ModulePDF
)
from .admin_actions import publish_courses, unpublish_courses, export_courses_csv, duplicate_course

class CourseAdminForm(forms.ModelForm):
    curriculum = forms.CharField(
        widget=forms.Textarea(attrs={
            'class': 'rich-text-editor',
            'rows': 10,
            'placeholder': 'Enter detailed curriculum outline using rich text formatting...'
        }),
        required=False,
        help_text='Detailed curriculum outline - what topics will be covered'
    )
    
    what_you_will_learn = forms.CharField(
        widget=forms.Textarea(attrs={
            'class': 'rich-text-editor', 
            'rows': 10,
            'placeholder': 'Describe what students will learn and achieve...'
        }),
        required=False,
        help_text='Learning outcomes - what students will achieve after completing the course'
    )
    
    class Meta:
        model = Course
        fields = '__all__'

class ModuleInline(admin.TabularInline):
    model = CourseModule
    extra = 1
    fields = ('module', 'order')
    ordering = ('order',)

class VideoLessonInline(admin.TabularInline):
    model = ModuleVideo
    extra = 1
    fields = ('video_lesson', 'order')
    readonly_fields = ()
    ordering = ('order',)

class AssignmentInline(admin.TabularInline):
    model = ModuleAssignment
    extra = 0
    fields = ('assignment', 'order')
    ordering = ('order',)

class QuizInline(admin.TabularInline):
    model = ModuleQuiz
    extra = 0
    fields = ('quiz', 'order')
    ordering = ('order',)

class CourseAssignmentInline(admin.TabularInline):
    model = CourseAssignment
    extra = 0
    fields = ('assignment', 'order')
    ordering = ('order',)
    verbose_name = "Course Assignment"
    verbose_name_plural = "Course Assignments"

class CourseQuizInline(admin.TabularInline):
    model = CourseQuiz
    extra = 0
    fields = ('quiz', 'order')
    ordering = ('order',)
    verbose_name = "Course Quiz"
    verbose_name_plural = "Course Quizzes"

class CoursePDFInline(admin.TabularInline):
    model = CoursePDF
    extra = 0
    fields = ('pdf_note', 'order')
    ordering = ('order',)
    verbose_name = "Course PDF Note"
    verbose_name_plural = "Course PDF Notes"

class ModulePDFInline(admin.TabularInline):
    model = ModulePDF
    extra = 0
    fields = ('pdf_note', 'order')
    ordering = ('order',)
    verbose_name = "Module PDF Note"
    verbose_name_plural = "Module PDF Notes"

class VideoAssignmentInline(admin.TabularInline):
    model = VideoAssignment
    extra = 0
    fields = ('assignment', 'order')
    ordering = ('order',)
    verbose_name = "Video Assignment"
    verbose_name_plural = "Video Assignments"

class VideoQuizInline(admin.TabularInline):
    model = VideoQuiz
    extra = 0
    fields = ('quiz', 'order')
    ordering = ('order',)
    verbose_name = "Video Quiz"
    verbose_name_plural = "Video Quizzes"

class VideoPDFInline(admin.TabularInline):
    model = VideoPDF
    extra = 0
    fields = ('pdf_note', 'order')
    ordering = ('order',)
    verbose_name = "Video PDF Note"
    verbose_name_plural = "Video PDF Notes"

@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'description', 'created_at')
    search_fields = ('name',)
    ordering = ('name',)

@admin.register(Course)
class CourseAdmin(admin.ModelAdmin):
    form = CourseAdminForm
    list_display = ('title', 'category', 'price_display_admin', 'total_price_display_admin', 'is_free', 'is_published', 'allow_public_enrollment', 'created_by', 'created_at')
    list_filter = ('category', 'is_free', 'is_published', 'allow_public_enrollment', 'created_at')
    search_fields = ('title', 'description', 'curriculum', 'what_you_will_learn')
    readonly_fields = ('is_free_course_display', 'total_price_display_formatted', 'tax_amount_display', 'price_display_formatted', 'total_price_display', 'created_at', 'updated_at')
    inlines = [ModuleInline, CourseAssignmentInline, CourseQuizInline, CoursePDFInline]
    actions = [publish_courses, unpublish_courses, export_courses_csv, duplicate_course]
    
    class Media:
        css = {
            'all': ('https://cdn.quilljs.com/1.3.6/quill.snow.css',)
        }
        js = (
            'https://cdn.quilljs.com/1.3.6/quill.min.js',
            'admin/js/rich_text_editor.js',
        )
    
    def price_display_admin(self, obj):
        return obj.price_display
    price_display_admin.short_description = 'Price'
    
    def total_price_display_admin(self, obj):
        return obj.total_price_display
    total_price_display_admin.short_description = 'Total Price'
    
    def is_free_course_display(self, obj):
        """Display if course is free with icon"""
        if obj.is_free_course:
            return "✅ Yes (Free Course)"
        return "❌ No (Paid Course)"
    is_free_course_display.short_description = 'Is Free Course'
    
    def total_price_display_formatted(self, obj):
        """Display total price with tax breakdown"""
        if obj.is_free_course:
            return "🆓 Free Course"
        return f"💰 ₹{obj.total_price:.2f} (including {obj.tax_rate}% tax)"
    total_price_display_formatted.short_description = 'Total Price (Inc. Tax)'
    
    def tax_amount_display(self, obj):
        """Display tax amount with formatting"""
        if obj.is_free_course:
            return "🆓 No Tax (Free Course)"
        return f"📊 ₹{obj.tax_amount:.2f} ({obj.tax_rate}% of ₹{obj.price})"
    tax_amount_display.short_description = 'Tax Amount'
    
    def price_display_formatted(self, obj):
        """Display base price with formatting"""
        if obj.is_free_course:
            return "🆓 Free Course"
        return f"💵 ₹{obj.price} (before tax)"
    price_display_formatted.short_description = 'Base Price (Ex. Tax)'
    
    fieldsets = (
        ('Course Information', {
            'fields': ('title', 'description', 'curriculum', 'what_you_will_learn', 'category', 'created_by')
        }),
        ('Pricing Configuration', {
            'fields': ('is_free', 'price', 'tax_rate'),
            'description': 'Set course pricing. Check "Is free" for free courses or set price to 0.',
            'classes': ('wide',)
        }),
        ('💰 Pricing Summary', {
            'fields': ('is_free_course_display', 'price_display_formatted', 'tax_amount_display', 'total_price_display_formatted'),
            'description': 'Calculated pricing information based on the configuration above.',
            'classes': ('collapse', 'wide')
        }),
        ('Media', {
            'fields': ('thumbnail', 'preview_video')
        }),
        ('Publication & Enrollment Settings', {
            'fields': ('is_published', 'allow_public_enrollment'),
            'description': 'Control course visibility and enrollment access. Uncheck "Allow public enrollment" for admin-only enrollment courses.'
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        })
    )

@admin.register(Module)
class ModuleAdmin(admin.ModelAdmin):
    list_display = ('title', 'difficulty_level', 'is_active', 'created_at')
    list_filter = ('difficulty_level', 'is_active', 'created_at')
    search_fields = ['title', 'description', 'tags']
    inlines = [VideoLessonInline, AssignmentInline, QuizInline, ModulePDFInline]

@admin.register(VideoLesson)
class VideoLessonAdmin(admin.ModelAdmin):
    list_display = ('title', 'platform', 'duration', 'is_preview', 'created_at')
    list_filter = ('platform', 'is_preview', 'created_at')
    search_fields = ['title', 'description', 'video_id']
    readonly_fields = ('created_at', 'updated_at')
    inlines = [VideoAssignmentInline, VideoQuizInline, VideoPDFInline]

@admin.register(StudentProgress)
class StudentProgressAdmin(admin.ModelAdmin):
    list_display = ('user', 'course', 'video_lesson', 'completed_percentage', 'completed', 'last_watched_at')
    list_filter = ('completed', 'course', 'last_watched_at')
    search_fields = ('user__name', 'user__email', 'course__title', 'video_lesson__title')
    readonly_fields = ('created_at', 'updated_at')


# Assignment and Quiz Admin Classes

class QuizChoiceInline(admin.TabularInline):
    model = QuizChoice
    extra = 2
    fields = ('choice_text', 'is_correct', 'order')
    ordering = ('order',)

class QuizQuestionInline(admin.StackedInline):
    model = QuizQuestion
    extra = 1
    fields = ('question_text', 'question_type', 'points', 'explanation', 'order')
    ordering = ('order',)


# Main Admin Classes for Assignments and Quizzes

@admin.register(Assignment)
class AssignmentAdmin(admin.ModelAdmin):
    list_display = ('title', 'max_points', 'passing_score', 'is_required', 'created_at')
    list_filter = ('is_required', 'created_at')
    search_fields = ['title', 'description', 'requirements']
    readonly_fields = ('created_at', 'updated_at')

    fieldsets = (
        ('Assignment Details', {
            'fields': ('title', 'description', 'requirements', 'resources')
        }),
        ('Scoring & Requirements', {
            'fields': ('max_points', 'passing_score', 'due_days', 'is_required')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        })
    )


@admin.register(Quiz)
class QuizAdmin(admin.ModelAdmin):
    list_display = ('title', 'total_questions', 'time_limit', 'passing_score', 'is_required', 'created_at')
    list_filter = ('is_required', 'created_at')
    search_fields = ['title', 'description']
    readonly_fields = ('total_questions', 'total_points', 'created_at', 'updated_at')
    inlines = [QuizQuestionInline]

    fieldsets = (
        ('Quiz Details', {
            'fields': ('title', 'description')
        }),
        ('Quiz Settings', {
            'fields': ('time_limit', 'max_attempts', 'passing_score', 'is_required')
        }),
        ('Display Options', {
            'fields': ('randomize_questions', 'show_results_immediately')
        }),
        ('Quiz Statistics', {
            'fields': ('total_questions', 'total_points'),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        })
    )


@admin.register(QuizQuestion)
class QuizQuestionAdmin(admin.ModelAdmin):
    list_display = ('quiz', 'question_text_short', 'question_type', 'points', 'order')
    list_filter = ('question_type',)
    search_fields = ('question_text', 'quiz__title')
    inlines = [QuizChoiceInline]
    
    def question_text_short(self, obj):
        return obj.question_text[:100] + "..." if len(obj.question_text) > 100 else obj.question_text
    question_text_short.short_description = 'Question'


@admin.register(AssignmentSubmission)
class AssignmentSubmissionAdmin(admin.ModelAdmin):
    list_display = ('student_name', 'assignment', 'status', 'score_display', 'submitted_at', 'graded_at')
    list_filter = ('status', 'submitted_at', 'graded_at')
    search_fields = ('student__name', 'student__email', 'assignment__title', 'github_url')
    readonly_fields = ('submitted_at', 'created_at', 'updated_at', 'score_percentage')
    
    def student_name(self, obj):
        return obj.student.name if hasattr(obj.student, 'name') else obj.student.username
    student_name.short_description = 'Student'
    
    def score_display(self, obj):
        if obj.score is None:
            return "Not graded"
        return f"{obj.score}/{obj.assignment.max_points} ({obj.score_percentage:.1f}%)"
    score_display.short_description = 'Score'
    
    fieldsets = (
        ('Submission Details', {
            'fields': ('assignment', 'student', 'github_url', 'submission_notes', 'status')
        }),
        ('Grading', {
            'fields': ('score', 'grade_comments', 'graded_by', 'graded_at', 'score_percentage'),
            'description': 'Admin grading section'
        }),
        ('Timestamps', {
            'fields': ('submitted_at', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        })
    )
    
    actions = ['mark_as_under_review', 'mark_as_graded']
    
    def mark_as_under_review(self, request, queryset):
        queryset.update(status='under_review')
        self.message_user(request, f"{queryset.count()} submissions marked as under review.")
    mark_as_under_review.short_description = "Mark selected submissions as under review"
    
    def mark_as_graded(self, request, queryset):
        graded_count = queryset.filter(score__isnull=False).update(status='graded')
        self.message_user(request, f"{graded_count} submissions marked as graded.")
    mark_as_graded.short_description = "Mark selected submissions as graded (only those with scores)"


@admin.register(QuizAttempt)
class QuizAttemptAdmin(admin.ModelAdmin):
    list_display = ('student_name', 'quiz', 'attempt_number', 'score_display', 'completed', 'started_at', 'completed_at')
    list_filter = ('completed', 'started_at')
    search_fields = ('student__name', 'student__email', 'quiz__title')
    readonly_fields = ('score_percentage', 'started_at', 'completed_at')
    
    def student_name(self, obj):
        return obj.student.name if hasattr(obj.student, 'name') else obj.student.username
    student_name.short_description = 'Student'
    
    def score_display(self, obj):
        return f"{obj.score}/{obj.total_points} ({obj.score_percentage:.1f}%)"
    score_display.short_description = 'Score'


@admin.register(ModuleProgress)
class ModuleProgressAdmin(admin.ModelAdmin):
    list_display = ('student_name', 'module', 'completion_percentage', 'is_completed', 'is_unlocked', 'completed_at')
    list_filter = ('is_completed', 'is_unlocked', 'completed_at')
    search_fields = ('student__name', 'student__email', 'module__title')
    readonly_fields = ('completion_percentage', 'started_at', 'completed_at', 'created_at', 'updated_at')
    
    def student_name(self, obj):
        return obj.student.name if hasattr(obj.student, 'name') else obj.student.username
    student_name.short_description = 'Student'
    
    actions = ['recalculate_progress']
    
    def recalculate_progress(self, request, queryset):
        updated_count = 0
        for progress in queryset:
            progress.check_completion()
            updated_count += 1
        self.message_user(request, f"Recalculated progress for {updated_count} modules.")
    recalculate_progress.short_description = "Recalculate progress for selected modules"


@admin.register(PDFNote)
class PDFNoteAdmin(admin.ModelAdmin):
    list_display = ('title', 'is_downloadable', 'file_size_display', 'page_count', 'created_at')
    list_filter = ('is_downloadable', 'created_at')
    search_fields = ('title', 'description')
    readonly_fields = ('file_size', 'created_at', 'updated_at')

    def file_size_display(self, obj):
        if not obj.file_size:
            return "N/A"
        # Convert bytes to MB
        size_mb = obj.file_size / (1024 * 1024)
        if size_mb < 1:
            size_kb = obj.file_size / 1024
            return f"{size_kb:.2f} KB"
        return f"{size_mb:.2f} MB"
    file_size_display.short_description = 'File Size'

    fieldsets = (
        ('PDF Information', {
            'fields': ('title', 'description', 'pdf_file')
        }),
        ('Settings', {
            'fields': ('is_downloadable',)
        }),
        ('File Details', {
            'fields': ('file_size', 'page_count'),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        })
    )
