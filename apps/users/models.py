from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.db import models
import uuid
import random
import string
from django.utils import timezone
from datetime import timedelta


class CustomUserManager(BaseUserManager):
    """Custom user manager for email-based authentication."""

    def create_user(self, email, name, password=None, **extra_fields):
        if not email:
            raise ValueError('The Email field must be set')
        email = self.normalize_email(email)
        user = self.model(email=email, name=name, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, name, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('is_active', True)
        extra_fields.setdefault('role', 'admin')

        if extra_fields.get('is_staff') is not True:
            raise ValueError('Superuser must have is_staff=True.')
        if extra_fields.get('is_superuser') is not True:
            raise ValueError('Superuser must have is_superuser=True.')

        return self.create_user(email, name, password, **extra_fields)


class User(AbstractUser):
    ROLE_CHOICES = [
        ('student', 'Student'),
        ('admin', 'Admin'),
        ('teacher', 'Teacher'),
    ]

    STUDENT_TYPE_CHOICES = [
        ('online', 'Online Only'),
        ('offline', 'Offline/Tuition Only'),
        ('both', 'Both Online & Offline'),
    ]

    username = models.CharField(max_length=150, unique=True, blank=True, null=True)
    email = models.EmailField(unique=True)
    name = models.CharField(max_length=150)
    role = models.CharField(max_length=15, choices=ROLE_CHOICES, default='student')
    phone_number = models.CharField(max_length=15, blank=True, null=True)
    address = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    # Student-specific fields
    student_type = models.CharField(
        max_length=10,
        choices=STUDENT_TYPE_CHOICES,
        default='online',
        help_text="Type of student: online courses, offline tuition, or both"
    )
    photo = models.ImageField(
        upload_to='students/photos/',
        blank=True,
        null=True,
        help_text="Student profile photo"
    )

    # Parent/Guardian information (for students)
    parent_name = models.CharField(max_length=150, blank=True, null=True, help_text="Parent/Guardian name")
    parent_phone = models.CharField(max_length=15, blank=True, null=True, help_text="Parent/Guardian phone")
    parent_email = models.EmailField(blank=True, null=True, help_text="Parent/Guardian email")

    # Academic information (for offline/tuition students)
    school_name = models.CharField(max_length=200, blank=True, null=True, help_text="School/College name")
    standard = models.ForeignKey(
        'tuition.Standard',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='user_students',
        help_text="Class/Standard for tuition students"
    )
    date_of_birth = models.DateField(blank=True, null=True, help_text="Date of birth")

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['name']

    objects = CustomUserManager()

    def __str__(self):
        return f"{self.name} ({self.email})"

    @property
    def is_online_student(self):
        return self.student_type in ['online', 'both']

    @property
    def is_offline_student(self):
        return self.student_type in ['offline', 'both']

    @property
    def student_type_display(self):
        return dict(self.STUDENT_TYPE_CHOICES).get(self.student_type, 'Online')

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

class PasswordResetCode(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='password_reset_codes')
    code = models.CharField(max_length=6, editable=False)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    is_used = models.BooleanField(default=False)
    
    def save(self, *args, **kwargs):
        if not self.code:
            # Generate a 6-digit numeric code
            self.code = ''.join(random.choices(string.digits, k=6))
        if not self.expires_at:
            # Code expires in 10 minutes
            self.expires_at = timezone.now() + timedelta(minutes=10)
        super().save(*args, **kwargs)
    
    def is_valid(self):
        return not self.is_used and timezone.now() < self.expires_at
    
    def __str__(self):
        return f"Password reset code {self.code} for {self.user.email}"
    
    class Meta:
        db_table = 'password_reset_codes'
        ordering = ['-created_at']

# Add a property to User model to get teams
User.add_to_class('teams', property(lambda self: Team.objects.filter(memberships__user=self, memberships__is_active=True)))
User.add_to_class('active_teams', property(lambda self: self.team_memberships.filter(is_active=True)))