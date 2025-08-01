from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.utils.html import format_html
from .models import User, Team, TeamMembership
from .admin_actions import export_users_csv, activate_users, deactivate_users

class TeamMembershipInline(admin.TabularInline):
    model = TeamMembership
    extra = 1
    fields = ('user', 'role', 'is_active', 'joined_at')
    readonly_fields = ('joined_at',)

@admin.register(User)
class UserAdmin(BaseUserAdmin):
    # Override the list display to show our custom fields
    list_display = ('email', 'name', 'role', 'is_active', 'date_joined')
    list_filter = ('role', 'is_active', 'date_joined', 'is_staff')
    search_fields = ('email', 'name', 'phone_number')
    ordering = ('-date_joined',)
    actions = [export_users_csv, activate_users, deactivate_users]
    
    # Override BaseUserAdmin fieldsets to include our custom fields
    fieldsets = BaseUserAdmin.fieldsets + (
        ('Custom Fields', {'fields': ('name', 'role', 'phone_number', 'address')}),
    )
    
    # Add fieldsets for creating new users
    add_fieldsets = BaseUserAdmin.add_fieldsets + (
        ('Custom Fields', {'fields': ('name', 'role', 'phone_number', 'address')}),
    )

@admin.register(Team)
class TeamAdmin(admin.ModelAdmin):
    list_display = ('name', 'team_leader', 'member_count_display', 'max_members', 'is_active', 'created_by', 'created_at')
    list_filter = ('is_active', 'created_at', 'max_members')
    search_fields = ('name', 'description', 'team_leader__name', 'created_by__name')
    inlines = [TeamMembershipInline]
    readonly_fields = ('member_count', 'available_spots', 'is_full', 'created_at', 'updated_at')
    
    def member_count_display(self, obj):
        count = obj.member_count
        max_members = obj.max_members
        if count >= max_members:
            return format_html('<span style="color: red;">{}/{}</span>', count, max_members)
        elif count >= max_members * 0.8:
            return format_html('<span style="color: orange;">{}/{}</span>', count, max_members)
        return format_html('<span style="color: green;">{}/{}</span>', count, max_members)
    member_count_display.short_description = 'Members'
    
    fieldsets = (
        ('Team Information', {
            'fields': ('name', 'description', 'team_leader', 'created_by')
        }),
        ('Team Settings', {
            'fields': ('max_members', 'is_active')
        }),
        ('Team Stats', {
            'fields': ('member_count', 'available_spots', 'is_full'),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        })
    )

@admin.register(TeamMembership)
class TeamMembershipAdmin(admin.ModelAdmin):
    list_display = ('user', 'team', 'role', 'joined_at', 'is_active')
    list_filter = ('role', 'is_active', 'joined_at')
    search_fields = ('user__name', 'user__email', 'team__name')
    readonly_fields = ('joined_at',)
    
    fieldsets = (
        ('Membership Details', {
            'fields': ('team', 'user', 'role', 'is_active')
        }),
        ('Timestamps', {
            'fields': ('joined_at',),
            'classes': ('collapse',)
        })
    )
