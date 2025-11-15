from django.db import models
from django.conf import settings
from django.utils import timezone
from apps.courses.models import Course
from apps.users.models import User, Team
import uuid


class LiveSession(models.Model):
    SESSION_STATUS_CHOICES = [
        ('scheduled', 'Scheduled'),
        ('live', 'Live'),
        ('ended', 'Ended'),
        ('cancelled', 'Cancelled'),
    ]

    ASSIGNMENT_TYPE_CHOICES = [
        ('course', 'Course Students'),
        ('individual', 'Individual Students'),
        ('team', 'Team Members'),
        ('manual', 'Manual Selection'),
    ]

    MEETING_LINK_TYPE_CHOICES = [
        ('auto', 'Auto (Google Workspace)'),
        ('manual', 'Manual Entry'),
    ]

    title = models.CharField(max_length=200, help_text="Session title")
    description = models.TextField(blank=True, null=True, help_text="Session description")

    # Meeting link configuration
    meeting_link_type = models.CharField(
        max_length=10,
        choices=MEETING_LINK_TYPE_CHOICES,
        default='auto',
        help_text="How meeting link is generated"
    )
    meeting_link = models.URLField(
        blank=True,
        null=True,
        help_text="Live session meeting link (auto-generated or manual)"
    )

    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name='live_sessions', null=True, blank=True, help_text="Associated course (optional)")

    # Scheduling
    scheduled_date = models.DateTimeField(help_text="When the session is scheduled")
    duration_minutes = models.PositiveIntegerField(default=60, help_text="Expected duration in minutes")

    # Assignment settings
    assignment_type = models.CharField(max_length=20, choices=ASSIGNMENT_TYPE_CHOICES, default='manual')

    # Status and tracking
    status = models.CharField(max_length=20, choices=SESSION_STATUS_CHOICES, default='scheduled')
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='created_sessions')
    max_participants = models.PositiveIntegerField(default=100, help_text="Maximum number of participants")

    # Session tracking
    started_at = models.DateTimeField(null=True, blank=True)
    ended_at = models.DateTimeField(null=True, blank=True)

    # Additional settings
    send_notifications = models.BooleanField(default=True, help_text="Send notifications to participants")
    allow_recording = models.BooleanField(default=False, help_text="Allow session recording")
    is_mandatory = models.BooleanField(default=False, help_text="Mandatory attendance for assigned students")

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.title} - {self.scheduled_date.strftime('%Y-%m-%d %H:%M')}"

    @property
    def is_upcoming(self):
        return self.status == 'scheduled' and self.scheduled_date > timezone.now()

    @property
    def is_live_now(self):
        return self.status == 'live'

    @property
    def participants_count(self):
        return self.participants.filter(status='assigned').count()

    @property
    def attended_count(self):
        return self.participants.filter(status='attended').count()

    @property
    def attendance_rate(self):
        if self.participants_count == 0:
            return 0
        return (self.attended_count / self.participants_count) * 100

    def start_session(self):
        """Mark session as live"""
        self.status = 'live'
        self.started_at = timezone.now()
        self.save()

        # Send notifications to participants
        if self.send_notifications:
            self._send_session_notifications('session_started')

    def end_session(self):
        """Mark session as ended"""
        self.status = 'ended'
        self.ended_at = timezone.now()
        self.save()

    def cancel_session(self):
        """Cancel the session"""
        self.status = 'cancelled'
        self.save()

        # Send notifications to participants
        if self.send_notifications:
            self._send_session_notifications('session_cancelled')

    def assign_course_students(self, course):
        """Assign all students enrolled in a course"""
        from apps.payments.models import Enrollment
        enrollments = Enrollment.objects.filter(course=course, active=True)

        for enrollment in enrollments:
            if enrollment.enrollment_type == 'team' and enrollment.team:
                # Add all team members
                for membership in enrollment.team.memberships.filter(is_active=True):
                    self.add_participant(membership.user)
            else:
                # Add individual student
                self.add_participant(enrollment.user)

    def assign_team_members(self, team):
        """Assign all members of a team"""
        for membership in team.memberships.filter(is_active=True):
            self.add_participant(membership.user)

    def add_participant(self, user):
        """Add a single participant"""
        try:
            participant, created = SessionParticipant.objects.get_or_create(
                session=self,
                student=user,
                defaults={'status': 'assigned'}
            )

            print(f"Debug: Participant {'created' if created else 'already exists'} for user {user.name}")

            # Send notification for new participant assignment
            if created and self.send_notifications:
                try:
                    self._send_user_notification(user, 'session_assigned')
                    print(f"Debug: Notification sent to {user.name}")
                except Exception as e:
                    print(f"Debug: Failed to send notification to {user.name}: {e}")

            return participant
        except Exception as e:
            print(f"Debug: Error in add_participant: {e}")
            raise e

    def get_unique_meeting_id(self):
        """Generate a unique meeting ID for the session"""
        return str(uuid.uuid4())[:8].upper()

    def _send_session_notifications(self, notification_type):
        """Send notifications to all session participants"""
        try:
            from apps.notifications.push_service import send_session_notification

            participants = self.participants.select_related('student').all()
            for participant in participants:
                try:
                    send_session_notification(
                        user=participant.student,
                        notification_type=notification_type,
                        session=self
                    )
                except Exception as e:
                    # Log error but don't fail the session operation
                    import logging
                    logger = logging.getLogger(__name__)
                    logger.error(f"Failed to send notification to user {participant.student.id}: {str(e)}")

        except ImportError:
            # Notification service not available
            pass

    def _send_user_notification(self, user, notification_type):
        """Send notification to a specific user"""
        try:
            from apps.notifications.push_service import send_session_notification

            send_session_notification(
                user=user,
                notification_type=notification_type,
                session=self
            )
        except ImportError:
            # Notification service not available
            pass
        except Exception as e:
            # Log error but don't fail the operation
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Failed to send notification to user {user.id}: {str(e)}")

    class Meta:
        db_table = 'live_sessions'
        ordering = ['-scheduled_date']


class SessionParticipant(models.Model):
    PARTICIPANT_STATUS_CHOICES = [
        ('assigned', 'Assigned'),
        ('notified', 'Notified'),
        ('attended', 'Attended'),
        ('missed', 'Missed'),
        ('excused', 'Excused'),
    ]

    session = models.ForeignKey(LiveSession, on_delete=models.CASCADE, related_name='participants')
    student = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='session_participations')
    status = models.CharField(max_length=20, choices=PARTICIPANT_STATUS_CHOICES, default='assigned')

    # Participation tracking
    joined_at = models.DateTimeField(null=True, blank=True)
    left_at = models.DateTimeField(null=True, blank=True)
    duration_minutes = models.PositiveIntegerField(null=True, blank=True, help_text="Total participation time")

    # Notifications
    notification_sent_at = models.DateTimeField(null=True, blank=True)
    reminder_sent_at = models.DateTimeField(null=True, blank=True)

    # Feedback
    feedback_rating = models.PositiveIntegerField(null=True, blank=True, help_text="Session rating 1-5")
    feedback_comments = models.TextField(blank=True, null=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.student.name} - {self.session.title}"

    def mark_attended(self):
        """Mark participant as attended"""
        self.status = 'attended'
        self.joined_at = timezone.now()
        self.save()

    def mark_left(self):
        """Mark participant as left and calculate duration"""
        if self.joined_at:
            duration = timezone.now() - self.joined_at
            self.duration_minutes = int(duration.total_seconds() / 60)
        self.left_at = timezone.now()
        self.save()

    def send_notification(self):
        """Mark notification as sent"""
        self.status = 'notified'
        self.notification_sent_at = timezone.now()
        self.save()

    @property
    def attendance_percentage(self):
        """Calculate attendance percentage for the session"""
        if not self.duration_minutes or not self.session.duration_minutes:
            return 0
        return min(100, (self.duration_minutes / self.session.duration_minutes) * 100)

    class Meta:
        db_table = 'session_participants'
        unique_together = ['session', 'student']
        ordering = ['student__name']


class SessionResource(models.Model):
    RESOURCE_TYPE_CHOICES = [
        ('presentation', 'Presentation'),
        ('document', 'Document'),
        ('video', 'Recording'),
        ('link', 'External Link'),
        ('assignment', 'Assignment'),
    ]

    session = models.ForeignKey(LiveSession, on_delete=models.CASCADE, related_name='resources')
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True, null=True)
    resource_type = models.CharField(max_length=20, choices=RESOURCE_TYPE_CHOICES)

    # File or link
    file = models.FileField(upload_to='session_resources/', blank=True, null=True)
    external_link = models.URLField(blank=True, null=True)

    # Availability
    available_before_session = models.BooleanField(default=True)
    available_during_session = models.BooleanField(default=True)
    available_after_session = models.BooleanField(default=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.session.title} - {self.title}"

    class Meta:
        db_table = 'session_resources'
        ordering = ['title']


class SessionAnnouncement(models.Model):
    ANNOUNCEMENT_TYPE_CHOICES = [
        ('general', 'General'),
        ('reminder', 'Reminder'),
        ('update', 'Session Update'),
        ('cancelled', 'Cancellation'),
        ('rescheduled', 'Rescheduled'),
    ]

    session = models.ForeignKey(LiveSession, on_delete=models.CASCADE, related_name='announcements')
    title = models.CharField(max_length=200)
    message = models.TextField()
    announcement_type = models.CharField(max_length=20, choices=ANNOUNCEMENT_TYPE_CHOICES, default='general')

    # Targeting
    send_to_all = models.BooleanField(default=True)
    specific_participants = models.ManyToManyField(
        SessionParticipant,
        blank=True,
        help_text="Leave empty to send to all participants"
    )

    # Delivery
    sent_at = models.DateTimeField(null=True, blank=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='session_announcements')

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.session.title} - {self.title}"

    def send_announcement(self):
        """Mark announcement as sent"""
        self.sent_at = timezone.now()
        self.save()

    class Meta:
        db_table = 'session_announcements'
        ordering = ['-created_at']