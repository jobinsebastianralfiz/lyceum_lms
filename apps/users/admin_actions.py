from django.contrib import admin
from django.http import HttpResponse
from django.shortcuts import render
from django.contrib import messages
import csv

def export_users_csv(modeladmin, request, queryset):
    """Export selected users to CSV file"""
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="users_export.csv"'
    
    writer = csv.writer(response)
    writer.writerow(['Name', 'Email', 'Role', 'Phone', 'Date Joined', 'Active'])
    
    for user in queryset:
        writer.writerow([
            user.name,
            user.email,
            user.role,
            user.phone_number or '',
            user.date_joined.strftime('%Y-%m-%d'),
            'Yes' if user.is_active else 'No'
        ])
    
    return response

export_users_csv.short_description = "Export selected users to CSV"

def activate_users(modeladmin, request, queryset):
    """Activate selected users"""
    updated = queryset.update(is_active=True)
    modeladmin.message_user(request, f'{updated} users were successfully activated.')

activate_users.short_description = "Activate selected users"

def deactivate_users(modeladmin, request, queryset):
    """Deactivate selected users"""
    updated = queryset.update(is_active=False)
    modeladmin.message_user(request, f'{updated} users were successfully deactivated.')

deactivate_users.short_description = "Deactivate selected users"