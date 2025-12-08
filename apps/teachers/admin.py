from django.contrib import admin
from .models import TeacherProfile, TeacherSchedule, TeacherAnnouncement


class TeacherScheduleInline(admin.TabularInline):
    model = TeacherSchedule
    extra = 0
    fields = ['day_of_week', 'start_time', 'end_time', 'course', 'is_active']


@admin.register(TeacherProfile)
class TeacherProfileAdmin(admin.ModelAdmin):
    list_display = ['user', 'employee_id', 'designation', 'department', 'is_active', 'total_courses', 'created_at']
    list_filter = ['is_active', 'department', 'date_of_joining']
    search_fields = ['user__name', 'user__email', 'employee_id', 'designation']
    readonly_fields = ['employee_id', 'created_at', 'updated_at']
    filter_horizontal = ['assigned_courses']
    inlines = [TeacherScheduleInline]

    fieldsets = (
        ('User Information', {
            'fields': ('user', 'employee_id')
        }),
        ('Professional Details', {
            'fields': ('designation', 'department', 'qualification', 'specialization', 'experience_years')
        }),
        ('Profile', {
            'fields': ('bio', 'profile_photo')
        }),
        ('Employment', {
            'fields': ('date_of_joining', 'is_active')
        }),
        ('Security', {
            'fields': ('must_change_password', 'last_password_change')
        }),
        ('Course Assignments', {
            'fields': ('assigned_courses',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )


@admin.register(TeacherSchedule)
class TeacherScheduleAdmin(admin.ModelAdmin):
    list_display = ['teacher', 'day_of_week', 'start_time', 'end_time', 'course', 'is_active']
    list_filter = ['day_of_week', 'is_active', 'teacher']
    search_fields = ['teacher__user__name', 'course__title']


@admin.register(TeacherAnnouncement)
class TeacherAnnouncementAdmin(admin.ModelAdmin):
    list_display = ['title', 'teacher', 'course', 'is_global', 'publish_at', 'is_active']
    list_filter = ['is_active', 'is_global', 'teacher']
    search_fields = ['title', 'content', 'teacher__user__name']
    readonly_fields = ['created_at', 'updated_at']
