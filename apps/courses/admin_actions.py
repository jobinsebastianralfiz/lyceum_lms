from django.contrib import admin
from django.http import HttpResponse
from django.shortcuts import render
from django.contrib import messages
import csv

def publish_courses(modeladmin, request, queryset):
    """Publish selected courses"""
    updated = queryset.update(is_published=True)
    modeladmin.message_user(request, f'{updated} courses were successfully published.')

publish_courses.short_description = "Publish selected courses"

def unpublish_courses(modeladmin, request, queryset):
    """Unpublish selected courses"""
    updated = queryset.update(is_published=False)
    modeladmin.message_user(request, f'{updated} courses were successfully unpublished.')

unpublish_courses.short_description = "Unpublish selected courses"

def export_courses_csv(modeladmin, request, queryset):
    """Export selected courses to CSV file"""
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="courses_export.csv"'
    
    writer = csv.writer(response)
    writer.writerow(['Title', 'Category', 'Price', 'Tax Rate', 'Total Price', 'Published', 'Created By', 'Created Date'])
    
    for course in queryset:
        writer.writerow([
            course.title,
            course.category.name,
            course.price,
            course.tax_rate,
            course.total_price,
            'Yes' if course.is_published else 'No',
            course.created_by.name,
            course.created_at.strftime('%Y-%m-%d')
        ])
    
    return response

export_courses_csv.short_description = "Export selected courses to CSV"

def duplicate_course(modeladmin, request, queryset):
    """Duplicate selected courses"""
    for course in queryset:
        # Create a copy of the course
        course_copy = course
        course_copy.pk = None
        course_copy.title = f"{course.title} (Copy)"
        course_copy.is_published = False
        course_copy.save()
        
        # Copy modules and videos
        for module in course.modules.all():
            module_copy = module
            module_copy.pk = None
            module_copy.course = course_copy
            module_copy.save()
            
            for video in module.video_lessons.all():
                video_copy = video
                video_copy.pk = None
                video_copy.module = module_copy
                video_copy.save()
    
    modeladmin.message_user(request, f'{queryset.count()} courses were successfully duplicated.')

duplicate_course.short_description = "Duplicate selected courses"