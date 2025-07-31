from django.contrib import admin
from .models import Category, Course, Module, VideoLesson, StudentProgress
from .admin_actions import publish_courses, unpublish_courses, export_courses_csv, duplicate_course

class ModuleInline(admin.TabularInline):
    model = Module
    extra = 1
    fields = ('title', 'order')
    ordering = ('order',)

class VideoLessonInline(admin.TabularInline):
    model = VideoLesson
    extra = 1
    fields = ('title', 'youtube_video_id', 'youtube_url', 'duration', 'order', 'is_preview')
    readonly_fields = ()
    ordering = ('order',)

@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'description', 'created_at')
    search_fields = ('name',)
    ordering = ('name',)

@admin.register(Course)
class CourseAdmin(admin.ModelAdmin):
    list_display = ('title', 'category', 'price_display_admin', 'total_price_display_admin', 'is_free', 'is_published', 'created_by', 'created_at')
    list_filter = ('category', 'is_free', 'is_published', 'created_at')
    search_fields = ('title', 'description')
    readonly_fields = ('is_free_course', 'total_price', 'tax_amount', 'price_display', 'total_price_display', 'created_at', 'updated_at')
    inlines = [ModuleInline]
    actions = [publish_courses, unpublish_courses, export_courses_csv, duplicate_course]
    
    def price_display_admin(self, obj):
        return obj.price_display
    price_display_admin.short_description = 'Price'
    
    def total_price_display_admin(self, obj):
        return obj.total_price_display
    total_price_display_admin.short_description = 'Total Price'
    
    fieldsets = (
        ('Course Information', {
            'fields': ('title', 'description', 'category', 'created_by')
        }),
        ('Pricing', {
            'fields': ('is_free', 'price', 'tax_rate', 'is_free_course', 'total_price', 'tax_amount', 'price_display', 'total_price_display'),
            'description': 'For free courses, check "Is free" or set price to 0'
        }),
        ('Media', {
            'fields': ('thumbnail', 'preview_video')
        }),
        ('Status', {
            'fields': ('is_published',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        })
    )

@admin.register(Module)
class ModuleAdmin(admin.ModelAdmin):
    list_display = ('title', 'course', 'order', 'created_at')
    list_filter = ('course', 'created_at')
    search_fields = ('title', 'course__title')
    inlines = [VideoLessonInline]

@admin.register(VideoLesson)
class VideoLessonAdmin(admin.ModelAdmin):
    list_display = ('title', 'module', 'youtube_video_id', 'duration', 'is_preview', 'order')
    list_filter = ('module__course', 'is_preview', 'created_at')
    search_fields = ('title', 'youtube_video_id', 'module__title')
    readonly_fields = ('youtube_url', 'created_at', 'updated_at')

@admin.register(StudentProgress)
class StudentProgressAdmin(admin.ModelAdmin):
    list_display = ('user', 'course', 'video_lesson', 'completed_percentage', 'completed', 'last_watched_at')
    list_filter = ('completed', 'course', 'last_watched_at')
    search_fields = ('user__name', 'user__email', 'course__title', 'video_lesson__title')
    readonly_fields = ('created_at', 'updated_at')
