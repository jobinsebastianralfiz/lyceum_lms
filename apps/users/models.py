from django.contrib.auth.models import AbstractUser
from django.db import models
import uuid
from django.utils import timezone
from datetime import timedelta

class User(AbstractUser):
    ROLE_CHOICES = [
        ('student', 'Student'),
        ('admin', 'Admin'),
    ]
    
    username = models.CharField(max_length=150, unique=True, blank=True, null=True)
    email = models.EmailField(unique=True)
    name = models.CharField(max_length=150)
    role = models.CharField(max_length=10, choices=ROLE_CHOICES, default='student')
    phone_number = models.CharField(max_length=15, blank=True, null=True)
    address = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['name']
    
    def __str__(self):
        return f"{self.name} ({self.email})"
    
    class Meta:
        db_table = 'users'

class Team(models.Model):
    name = models.CharField(max_length=100, help_text="Team name")
    description = models.TextField(blank=True, null=True, help_text="Team description")
    team_leader = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='led_teams', help_text="Team leader (optional)")
    max_members = models.PositiveIntegerField(default=5, help_text="Maximum number of team members")
    is_active = models.BooleanField(default=True)
    created_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='created_teams')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return self.name
    
    @property
    def member_count(self):
        return self.memberships.filter(is_active=True).count()
    
    @property
    def available_spots(self):
        return max(0, self.max_members - self.member_count)
    
    @property
    def is_full(self):
        return self.member_count >= self.max_members
    
    class Meta:
        db_table = 'teams'
        ordering = ['name']

class TeamMembership(models.Model):
    ROLE_CHOICES = [
        ('member', 'Member'),
        ('leader', 'Leader'),
    ]
    
    team = models.ForeignKey(Team, on_delete=models.CASCADE, related_name='memberships')
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='team_memberships')
    role = models.CharField(max_length=10, choices=ROLE_CHOICES, default='member')
    joined_at = models.DateTimeField(auto_now_add=True)
    is_active = models.BooleanField(default=True)
    
    def __str__(self):
        return f"{self.user.name} - {self.team.name} ({self.role})"
    
    class Meta:
        db_table = 'team_memberships'
        unique_together = ['team', 'user']
        ordering = ['joined_at']

class PasswordResetToken(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='password_reset_tokens')
    token = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    is_used = models.BooleanField(default=False)
    
    def save(self, *args, **kwargs):
        if not self.expires_at:
            self.expires_at = timezone.now() + timedelta(hours=24)
        super().save(*args, **kwargs)
    
    def is_valid(self):
        return not self.is_used and timezone.now() < self.expires_at
    
    def __str__(self):
        return f"Password reset token for {self.user.email}"
    
    class Meta:
        db_table = 'password_reset_tokens'
        ordering = ['-created_at']

# Add a property to User model to get teams
User.add_to_class('teams', property(lambda self: Team.objects.filter(memberships__user=self, memberships__is_active=True)))
User.add_to_class('active_teams', property(lambda self: self.team_memberships.filter(is_active=True)))