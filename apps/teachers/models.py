from django.db import models
from django.conf import settings
from django.utils import timezone


class TeacherProfile(models.Model):
    """Extended profile information for teachers - handles both online courses and offline tuition"""
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='teacher_profile'
    )

    # Professional Information
    employee_id = models.CharField(max_length=50, unique=True, blank=True, null=True, help_text="Unique employee identifier")
    designation = models.CharField(max_length=100, blank=True, null=True, help_text="e.g., Senior Instructor, Professor")
    department = models.CharField(max_length=100, blank=True, null=True, help_text="Subject area/department")

    # Qualifications
    qualification = models.TextField(blank=True, null=True, help_text="Educational qualifications")
    specialization = models.TextField(blank=True, null=True, help_text="Areas of expertise")
    experience_years = models.PositiveIntegerField(default=0, help_text="Years of teaching experience")

    # Bio and Profile
    bio = models.TextField(blank=True, null=True, help_text="Short biography")
    profile_photo = models.ImageField(upload_to='teacher_photos/', blank=True, null=True)

    # Contact Information (additional)
    alternate_phone = models.CharField(max_length=20, blank=True, null=True, help_text="Alternate contact number")
    address = models.TextField(blank=True, null=True, help_text="Residential address")

    # Employment Details
    date_of_joining = models.DateField(blank=True, null=True, help_text="Employment start date")
    is_active = models.BooleanField(default=True)

    # First login tracking for password change
    must_change_password = models.BooleanField(default=True, help_text="Force password change on first login")
    last_password_change = models.DateTimeField(blank=True, null=True)

    # === ONLINE COURSES ===
    # Assigned Courses (Many-to-Many)
    assigned_courses = models.ManyToManyField(
        'courses.Course',
        related_name='assigned_teachers',
        blank=True,
        help_text="Online courses assigned to this teacher"
    )

    # === OFFLINE TUITION ===
    # Subjects they can teach (for tuition)
    tuition_subjects = models.ManyToManyField(
        'tuition.Subject',
        related_name='teachers',
        blank=True,
        help_text="Offline tuition subjects this teacher can teach"
    )

    # Teaching mode flags
    can_teach_online = models.BooleanField(default=True, help_text="Can teach online courses")
    can_teach_offline = models.BooleanField(default=True, help_text="Can teach offline tuition batches")

    # === PAYMENT/BANK DETAILS ===
    bank_name = models.CharField(max_length=100, blank=True, null=True)
    account_number = models.CharField(max_length=50, blank=True, null=True)
    ifsc_code = models.CharField(max_length=20, blank=True, null=True)
    upi_id = models.CharField(max_length=100, blank=True, null=True)

    # Notes
    notes = models.TextField(blank=True, null=True, help_text="Internal notes about the teacher")

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'teacher_profiles'
        verbose_name = 'Teacher Profile'
        verbose_name_plural = 'Teacher Profiles'

    def __str__(self):
        return f"{self.user.name} - {self.designation or 'Teacher'}"

    def save(self, *args, **kwargs):
        # Auto-generate employee ID if not provided
        if not self.employee_id:
            year = timezone.now().year
            count = TeacherProfile.objects.filter(created_at__year=year).count() + 1
            self.employee_id = f"TCH-{year}-{count:04d}"
        super().save(*args, **kwargs)

    @property
    def full_name(self):
        return self.user.name

    @property
    def email(self):
        return self.user.email

    @property
    def phone(self):
        return self.user.phone_number

    @property
    def total_students(self):
        """Get total students across all assigned courses"""
        from apps.payments.models import Enrollment
        return Enrollment.objects.filter(
            course__in=self.assigned_courses.all(),
            active=True
        ).values('user').distinct().count()

    @property
    def total_courses(self):
        return self.assigned_courses.count()

    @property
    def active_batches(self):
        """Get active tuition batches assigned to this teacher"""
        return self.teaching_batches.filter(is_active=True)

    @property
    def total_batches(self):
        """Count of active tuition batches"""
        return self.teaching_batches.filter(is_active=True).count()

    @property
    def total_tuition_students(self):
        """Get total students across all tuition batches"""
        from apps.tuition.models import TuitionEnrollment
        return TuitionEnrollment.objects.filter(
            batch__teacher=self,
            is_active=True
        ).values('student').distinct().count()


class TeacherSchedule(models.Model):
    """Schedule/timetable for teachers"""
    DAY_CHOICES = [
        ('monday', 'Monday'),
        ('tuesday', 'Tuesday'),
        ('wednesday', 'Wednesday'),
        ('thursday', 'Thursday'),
        ('friday', 'Friday'),
        ('saturday', 'Saturday'),
        ('sunday', 'Sunday'),
    ]

    teacher = models.ForeignKey(
        TeacherProfile,
        on_delete=models.CASCADE,
        related_name='schedules'
    )
    course = models.ForeignKey(
        'courses.Course',
        on_delete=models.CASCADE,
        related_name='teacher_schedules',
        null=True,
        blank=True
    )

    day_of_week = models.CharField(max_length=10, choices=DAY_CHOICES)
    start_time = models.TimeField()
    end_time = models.TimeField()

    # Optional batch/tuition reference
    batch = models.ForeignKey(
        'tuition.TuitionBatch',
        on_delete=models.CASCADE,
        related_name='teacher_schedules',
        null=True,
        blank=True
    )

    is_active = models.BooleanField(default=True)
    notes = models.TextField(blank=True, null=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'teacher_schedules'
        ordering = ['day_of_week', 'start_time']

    def __str__(self):
        return f"{self.teacher.user.name} - {self.day_of_week} ({self.start_time} - {self.end_time})"


class TeacherAnnouncement(models.Model):
    """Announcements made by teachers to their students"""
    teacher = models.ForeignKey(
        TeacherProfile,
        on_delete=models.CASCADE,
        related_name='announcements'
    )
    course = models.ForeignKey(
        'courses.Course',
        on_delete=models.CASCADE,
        related_name='teacher_announcements',
        null=True,
        blank=True,
        help_text="Leave blank for all courses"
    )

    title = models.CharField(max_length=200)
    content = models.TextField()

    # Target
    is_global = models.BooleanField(default=False, help_text="Visible to all teacher's students")

    # Scheduling
    publish_at = models.DateTimeField(default=timezone.now)
    expires_at = models.DateTimeField(blank=True, null=True)

    is_active = models.BooleanField(default=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'teacher_announcements'
        ordering = ['-publish_at']

    def __str__(self):
        return f"{self.title} by {self.teacher.user.name}"

    @property
    def is_published(self):
        now = timezone.now()
        if self.publish_at > now:
            return False
        if self.expires_at and self.expires_at < now:
            return False
        return self.is_active
