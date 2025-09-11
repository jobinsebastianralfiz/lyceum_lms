from django.contrib import admin
from .models import CourseRating, CourseReview, ReviewHelpful


@admin.register(CourseRating)
class CourseRatingAdmin(admin.ModelAdmin):
    list_display = ('course', 'user', 'rating', 'star_display', 'is_approved', 'created_at')
    list_filter = ('rating', 'is_approved', 'created_at', 'course')
    search_fields = ('course__title', 'user__username', 'user__email', 'review_text')
    readonly_fields = ('created_at', 'updated_at')
    list_editable = ('is_approved',)
    
    fieldsets = (
        (None, {
            'fields': ('course', 'user', 'rating', 'review_text')
        }),
        ('Moderation', {
            'fields': ('is_approved',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )


@admin.register(CourseReview)
class CourseReviewAdmin(admin.ModelAdmin):
    list_display = ('title', 'course', 'user', 'get_rating', 'is_helpful_count', 'is_approved', 'created_at')
    list_filter = ('is_approved', 'created_at', 'course', 'rating__rating')
    search_fields = ('title', 'content', 'course__title', 'user__username')
    readonly_fields = ('created_at', 'updated_at', 'is_helpful_count')
    list_editable = ('is_approved',)
    
    def get_rating(self, obj):
        return f"{obj.rating.rating} ★"
    get_rating.short_description = 'Rating'
    get_rating.admin_order_field = 'rating__rating'
    
    fieldsets = (
        (None, {
            'fields': ('course', 'user', 'rating', 'title', 'content')
        }),
        ('Statistics', {
            'fields': ('is_helpful_count',)
        }),
        ('Moderation', {
            'fields': ('is_approved',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )


@admin.register(ReviewHelpful)
class ReviewHelpfulAdmin(admin.ModelAdmin):
    list_display = ('review', 'user', 'is_helpful', 'created_at')
    list_filter = ('is_helpful', 'created_at')
    search_fields = ('review__title', 'user__username', 'review__course__title')
    readonly_fields = ('created_at',)
    
    def has_add_permission(self, request):
        # Usually users vote through the frontend
        return False