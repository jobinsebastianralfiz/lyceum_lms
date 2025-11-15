from rest_framework import serializers
from django.contrib.auth import get_user_model
from apps.courses.models import Course
from apps.users.models import Team
from .models import LiveSession, SessionParticipant, SessionResource, SessionAnnouncement

User = get_user_model()


class LiveSessionListSerializer(serializers.ModelSerializer):
    """Serializer for listing live sessions"""
    course_title = serializers.CharField(source='course.title', read_only=True)
    created_by_name = serializers.CharField(source='created_by.name', read_only=True)
    participants_count = serializers.SerializerMethodField()
    is_upcoming = serializers.SerializerMethodField()

    class Meta:
        model = LiveSession
        fields = [
            'id', 'title', 'description', 'meeting_link_type', 'meeting_link',
            'course', 'course_title', 'scheduled_date', 'duration_minutes',
            'status', 'created_by', 'created_by_name', 'max_participants',
            'participants_count', 'is_upcoming', 'created_at'
        ]

    def get_participants_count(self, obj):
        return obj.participants_count

    def get_is_upcoming(self, obj):
        return obj.is_upcoming


class SessionParticipantSerializer(serializers.ModelSerializer):
    """Serializer for session participants"""
    student_name = serializers.CharField(source='student.name', read_only=True)
    student_email = serializers.CharField(source='student.email', read_only=True)

    class Meta:
        model = SessionParticipant
        fields = [
            'id', 'student', 'student_name', 'student_email', 'status',
            'joined_at', 'left_at', 'duration_minutes', 'created_at'
        ]


class SessionResourceSerializer(serializers.ModelSerializer):
    """Serializer for session resources"""

    class Meta:
        model = SessionResource
        fields = [
            'id', 'title', 'description', 'resource_type', 'file', 'external_link',
            'available_before_session', 'available_during_session', 'available_after_session',
            'created_at'
        ]


class SessionAnnouncementSerializer(serializers.ModelSerializer):
    """Serializer for session announcements"""
    created_by_name = serializers.CharField(source='created_by.name', read_only=True)

    class Meta:
        model = SessionAnnouncement
        fields = [
            'id', 'title', 'message', 'announcement_type', 'send_to_all',
            'sent_at', 'created_by', 'created_by_name', 'created_at'
        ]


class LiveSessionDetailSerializer(serializers.ModelSerializer):
    """Detailed serializer for live sessions"""
    course_title = serializers.CharField(source='course.title', read_only=True)
    created_by_name = serializers.CharField(source='created_by.name', read_only=True)
    participants = SessionParticipantSerializer(many=True, read_only=True)
    resources = SessionResourceSerializer(many=True, read_only=True)
    announcements = SessionAnnouncementSerializer(many=True, read_only=True)
    participants_count = serializers.SerializerMethodField()
    attended_count = serializers.SerializerMethodField()
    attendance_rate = serializers.SerializerMethodField()
    is_upcoming = serializers.SerializerMethodField()
    is_live_now = serializers.SerializerMethodField()

    class Meta:
        model = LiveSession
        fields = [
            'id', 'title', 'description', 'meeting_link_type', 'meeting_link',
            'course', 'course_title', 'scheduled_date', 'duration_minutes',
            'assignment_type', 'status', 'created_by', 'created_by_name',
            'max_participants', 'send_notifications', 'allow_recording',
            'is_mandatory', 'started_at', 'ended_at', 'participants_count',
            'attended_count', 'attendance_rate', 'is_upcoming', 'is_live_now',
            'participants', 'resources', 'announcements', 'created_at', 'updated_at'
        ]

    def get_participants_count(self, obj):
        return obj.participants_count

    def get_attended_count(self, obj):
        return obj.attended_count

    def get_attendance_rate(self, obj):
        return obj.attendance_rate

    def get_is_upcoming(self, obj):
        return obj.is_upcoming

    def get_is_live_now(self, obj):
        return obj.is_live_now


class LiveSessionCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating live sessions"""

    class Meta:
        model = LiveSession
        fields = [
            'title', 'description', 'meeting_link_type', 'meeting_link', 'course',
            'scheduled_date', 'duration_minutes', 'assignment_type', 'max_participants',
            'send_notifications', 'allow_recording', 'is_mandatory'
        ]

    def validate(self, data):
        """Validate meeting link based on type"""
        meeting_link_type = data.get('meeting_link_type', 'auto')
        meeting_link = data.get('meeting_link')

        # If manual type, meeting_link is required
        if meeting_link_type == 'manual' and not meeting_link:
            raise serializers.ValidationError({
                'meeting_link': 'Meeting link is required when using manual mode.'
            })

        # If auto type and link is provided, check if Google Workspace is configured
        if meeting_link_type == 'auto' and meeting_link:
            # Allow manual override even in auto mode
            pass

        return data

    def validate_scheduled_date(self, value):
        """Ensure session is not scheduled in the past"""
        from django.utils import timezone
        if value <= timezone.now():
            raise serializers.ValidationError("Session cannot be scheduled in the past.")
        return value

    def create(self, validated_data):
        """Create live session with the current user as creator"""
        validated_data['created_by'] = self.context['request'].user
        meeting_link_type = validated_data.get('meeting_link_type', 'auto')

        # Create the session first
        session = super().create(validated_data)

        # If auto mode and no manual link provided, try to create Google Meet
        if meeting_link_type == 'auto' and not session.meeting_link:
            try:
                from system_settings.google_meet_service import GoogleMeetService
                from system_settings.models import GoogleWorkspaceIntegration

                # Check if Google Workspace is configured
                workspace = GoogleWorkspaceIntegration.objects.filter(
                    admin_user=self.context['request'].user,
                    is_active=True
                ).first()

                if workspace:
                    meet_service = GoogleMeetService(self.context['request'].user)
                    meet_service.create_meet_session(session)
                else:
                    # No workspace configured, require manual link
                    session.meeting_link_type = 'manual'
                    session.save(update_fields=['meeting_link_type'])
            except Exception as e:
                # If Google Meet creation fails, fall back to manual
                print(f"Google Meet creation failed: {e}")
                session.meeting_link_type = 'manual'
                session.save(update_fields=['meeting_link_type'])

        return session


class StudentLiveSessionSerializer(serializers.ModelSerializer):
    """Serializer for live sessions from student perspective"""
    course_title = serializers.CharField(source='course.title', read_only=True)
    my_participation = serializers.SerializerMethodField()
    is_upcoming = serializers.SerializerMethodField()
    is_live_now = serializers.SerializerMethodField()
    time_until_session = serializers.SerializerMethodField()
    can_join = serializers.SerializerMethodField()

    class Meta:
        model = LiveSession
        fields = [
            'id', 'title', 'description', 'meeting_link_type', 'meeting_link',
            'course', 'course_title', 'scheduled_date', 'duration_minutes',
            'status', 'max_participants', 'is_mandatory', 'allow_recording',
            'my_participation', 'is_upcoming', 'is_live_now', 'time_until_session',
            'can_join', 'created_at'
        ]

    def get_my_participation(self, obj):
        """Get current user's participation in this session"""
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            try:
                participation = obj.participants.get(student=request.user)
                return SessionParticipantSerializer(participation).data
            except SessionParticipant.DoesNotExist:
                return None
        return None

    def get_is_upcoming(self, obj):
        return obj.is_upcoming

    def get_is_live_now(self, obj):
        return obj.is_live_now

    def get_time_until_session(self, obj):
        """Get time until session starts (in minutes)"""
        from django.utils import timezone
        if obj.scheduled_date > timezone.now():
            delta = obj.scheduled_date - timezone.now()
            return int(delta.total_seconds() / 60)
        return 0

    def get_can_join(self, obj):
        """Check if current user can join this session"""
        request = self.context.get('request')
        if not request or not request.user.is_authenticated:
            return False

        # Check if user is assigned to this session
        try:
            participation = obj.participants.get(student=request.user)
            # Can join if session is live or about to start (within 15 minutes)
            if obj.status == 'live':
                return True
            elif obj.status == 'scheduled':
                from django.utils import timezone
                from datetime import timedelta
                time_until = obj.scheduled_date - timezone.now()
                return time_until <= timedelta(minutes=15)
        except SessionParticipant.DoesNotExist:
            pass

        return False


class SessionParticipantActionSerializer(serializers.Serializer):
    """Serializer for participant actions (join/leave)"""
    action = serializers.ChoiceField(choices=['join', 'leave'])

    def validate_action(self, value):
        session = self.context['session']
        user = self.context['request'].user

        # Check if user is assigned to this session
        try:
            participation = session.participants.get(student=user)
        except SessionParticipant.DoesNotExist:
            raise serializers.ValidationError("You are not assigned to this session.")

        if value == 'join':
            if session.status != 'live':
                raise serializers.ValidationError("Session is not currently live.")
            if participation.status == 'attended':
                raise serializers.ValidationError("You have already joined this session.")

        elif value == 'leave':
            if participation.status != 'attended':
                raise serializers.ValidationError("You are not currently in this session.")

        return value


class BulkAssignParticipantsSerializer(serializers.Serializer):
    """Serializer for bulk assigning participants to a session"""
    assignment_type = serializers.ChoiceField(choices=[
        ('course_students', 'All students from selected course'),
        ('team_members', 'All members from selected team'),
        ('individual_students', 'Selected individual students'),
    ])
    course = serializers.PrimaryKeyRelatedField(
        queryset=Course.objects.filter(is_published=True),
        required=False,
        allow_null=True
    )
    team = serializers.PrimaryKeyRelatedField(
        queryset=Team.objects.filter(is_active=True),
        required=False,
        allow_null=True
    )
    students = serializers.PrimaryKeyRelatedField(
        queryset=User.objects.filter(role='student', is_active=True),
        many=True,
        required=False,
        allow_empty=True
    )

    def validate(self, data):
        assignment_type = data.get('assignment_type')
        course = data.get('course')
        team = data.get('team')
        students = data.get('students', [])

        if assignment_type == 'course_students' and not course:
            raise serializers.ValidationError('Course is required when assigning course students.')

        if assignment_type == 'team_members' and not team:
            raise serializers.ValidationError('Team is required when assigning team members.')

        if assignment_type == 'individual_students' and not students:
            raise serializers.ValidationError('At least one student must be selected for individual assignment.')

        return data


class SessionStatusUpdateSerializer(serializers.Serializer):
    """Serializer for updating session status"""
    action = serializers.ChoiceField(choices=['start', 'end', 'cancel'])

    def validate_action(self, value):
        session = self.context['session']
        current_status = session.status

        if value == 'start' and current_status != 'scheduled':
            raise serializers.ValidationError("Can only start sessions that are scheduled.")

        if value == 'end' and current_status != 'live':
            raise serializers.ValidationError("Can only end sessions that are currently live.")

        if value == 'cancel' and current_status not in ['scheduled', 'live']:
            raise serializers.ValidationError("Can only cancel scheduled or live sessions.")

        return value