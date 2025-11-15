from rest_framework import generics, status, permissions
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
from django.db.models import Q
from django.utils import timezone
from apps.users.models import User, Team
from apps.courses.models import Course
from .models import LiveSession, SessionParticipant, SessionResource, SessionAnnouncement
from .serializers import (
    LiveSessionListSerializer, LiveSessionDetailSerializer, LiveSessionCreateSerializer,
    StudentLiveSessionSerializer, SessionParticipantActionSerializer,
    BulkAssignParticipantsSerializer, SessionStatusUpdateSerializer,
    SessionParticipantSerializer, SessionAnnouncementSerializer
)


class LiveSessionListView(generics.ListAPIView):
    """List all live sessions for students"""
    serializer_class = StudentLiveSessionSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        if user.role == 'admin':
            # Admins can see all sessions
            return LiveSession.objects.select_related('course', 'created_by').all()
        else:
            # Students can only see sessions they're assigned to
            return LiveSession.objects.filter(
                participants__student=user
            ).select_related('course', 'created_by').distinct()


class LiveSessionDetailView(generics.RetrieveAPIView):
    """Get live session details"""
    permission_classes = [permissions.IsAuthenticated]

    def get_serializer_class(self):
        user = self.request.user
        if user.role == 'admin':
            return LiveSessionDetailSerializer
        else:
            return StudentLiveSessionSerializer

    def get_queryset(self):
        user = self.request.user
        if user.role == 'admin':
            return LiveSession.objects.all()
        else:
            # Students can only see sessions they're assigned to
            return LiveSession.objects.filter(participants__student=user)


class AdminLiveSessionListView(generics.ListCreateAPIView):
    """Admin view for listing and creating live sessions"""
    permission_classes = [permissions.IsAuthenticated]

    def get_serializer_class(self):
        if self.request.method == 'POST':
            return LiveSessionCreateSerializer
        return LiveSessionListSerializer

    def get_queryset(self):
        # Only admins can access this view
        if self.request.user.role != 'admin':
            return LiveSession.objects.none()

        queryset = LiveSession.objects.select_related('course', 'created_by').all()

        # Filtering
        status_filter = self.request.query_params.get('status')
        course_filter = self.request.query_params.get('course')
        search = self.request.query_params.get('search')

        if status_filter:
            queryset = queryset.filter(status=status_filter)

        if course_filter:
            queryset = queryset.filter(course_id=course_filter)

        if search:
            queryset = queryset.filter(
                Q(title__icontains=search) |
                Q(description__icontains=search) |
                Q(course__title__icontains=search)
            )

        return queryset.order_by('-scheduled_date')


class AdminLiveSessionDetailView(generics.RetrieveUpdateDestroyAPIView):
    """Admin view for managing individual live sessions"""
    serializer_class = LiveSessionDetailSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        # Only admins can access this view
        if self.request.user.role != 'admin':
            return LiveSession.objects.none()
        return LiveSession.objects.all()


@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def session_participant_action(request, session_id):
    """Handle participant actions (join/leave session)"""
    session = get_object_or_404(LiveSession, id=session_id)
    serializer = SessionParticipantActionSerializer(
        data=request.data,
        context={'request': request, 'session': session}
    )

    if serializer.is_valid():
        action = serializer.validated_data['action']
        user = request.user

        try:
            participation = session.participants.get(student=user)

            if action == 'join':
                participation.mark_attended()
                return Response({
                    'success': True,
                    'message': 'Successfully joined the session',
                    'meeting_link': session.meeting_link
                })

            elif action == 'leave':
                participation.mark_left()
                return Response({
                    'success': True,
                    'message': 'Successfully left the session'
                })

        except SessionParticipant.DoesNotExist:
            return Response({
                'success': False,
                'error': 'You are not assigned to this session'
            }, status=status.HTTP_403_FORBIDDEN)

    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def bulk_assign_participants(request, session_id):
    """Bulk assign participants to a session (Admin only)"""
    if request.user.role != 'admin':
        return Response({
            'error': 'Admin access required'
        }, status=status.HTTP_403_FORBIDDEN)

    session = get_object_or_404(LiveSession, id=session_id)
    serializer = BulkAssignParticipantsSerializer(data=request.data)

    if serializer.is_valid():
        assignment_type = serializer.validated_data['assignment_type']
        assigned_count = 0

        if assignment_type == 'course_students':
            course = serializer.validated_data['course']
            session.assign_course_students(course)
            # Count enrolled students
            from apps.payments.models import Enrollment
            enrollments = Enrollment.objects.filter(course=course, active=True)
            for enrollment in enrollments:
                if enrollment.enrollment_type == 'team' and enrollment.team:
                    assigned_count += enrollment.team.memberships.filter(is_active=True).count()
                else:
                    assigned_count += 1

        elif assignment_type == 'team_members':
            team = serializer.validated_data['team']
            session.assign_team_members(team)
            assigned_count = team.memberships.filter(is_active=True).count()

        elif assignment_type == 'individual_students':
            students = serializer.validated_data['students']
            for student in students:
                session.add_participant(student)
            assigned_count = len(students)

        return Response({
            'success': True,
            'message': f'Successfully assigned {assigned_count} participants to the session'
        })

    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def session_status_update(request, session_id):
    """Update session status (start/end/cancel) - Admin only"""
    if request.user.role != 'admin':
        return Response({
            'error': 'Admin access required'
        }, status=status.HTTP_403_FORBIDDEN)

    session = get_object_or_404(LiveSession, id=session_id)
    serializer = SessionStatusUpdateSerializer(
        data=request.data,
        context={'session': session}
    )

    if serializer.is_valid():
        action = serializer.validated_data['action']

        if action == 'start':
            session.start_session()
            message = 'Session started successfully'

        elif action == 'end':
            session.end_session()
            message = 'Session ended successfully'

        elif action == 'cancel':
            session.cancel_session()
            message = 'Session cancelled successfully'

        return Response({
            'success': True,
            'message': message,
            'session': LiveSessionDetailSerializer(session).data
        })

    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def my_upcoming_sessions(request):
    """Get current user's upcoming sessions (scheduled and live)"""
    user = request.user
    upcoming_sessions = LiveSession.objects.filter(
        participants__student=user,
        status__in=['scheduled', 'live']  # Include both scheduled and live sessions
    ).select_related('course').order_by('scheduled_date')[:10]

    serializer = StudentLiveSessionSerializer(
        upcoming_sessions,
        many=True,
        context={'request': request}
    )

    return Response({
        'upcoming_sessions': serializer.data
    })


@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def session_participants(request, session_id):
    """Get session participants (Admin only)"""
    if request.user.role != 'admin':
        return Response({
            'error': 'Admin access required'
        }, status=status.HTTP_403_FORBIDDEN)

    session = get_object_or_404(LiveSession, id=session_id)
    participants = session.participants.select_related('student').all()

    serializer = SessionParticipantSerializer(participants, many=True)

    return Response({
        'participants': serializer.data,
        'total_count': participants.count(),
        'attended_count': participants.filter(status='attended').count()
    })


@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def add_session_participant(request, session_id):
    """Add individual participant to session (Admin only)"""
    if request.user.role != 'admin':
        return Response({
            'error': 'Admin access required'
        }, status=status.HTTP_403_FORBIDDEN)

    session = get_object_or_404(LiveSession, id=session_id)
    student_id = request.data.get('student_id')

    if not student_id:
        return Response({
            'error': 'student_id is required'
        }, status=status.HTTP_400_BAD_REQUEST)

    try:
        # Try to find the user first without role restriction to debug
        try:
            user = User.objects.get(id=student_id)
            print(f"Debug: Found user {user.name} with role {user.role}, active: {user.is_active}")
        except User.DoesNotExist:
            return Response({
                'error': f'User with ID {student_id} not found'
            }, status=status.HTTP_404_NOT_FOUND)

        # Now check if user is a student and active
        if user.role != 'student':
            return Response({
                'error': f'User {user.name} is not a student (role: {user.role})'
            }, status=status.HTTP_400_BAD_REQUEST)

        if not user.is_active:
            return Response({
                'error': f'User {user.name} is not active'
            }, status=status.HTTP_400_BAD_REQUEST)

        student = user

    except Exception as e:
        return Response({
            'error': f'Error finding student: {str(e)}'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    # Check if already assigned
    if session.participants.filter(student=student).exists():
        return Response({
            'error': 'Student is already assigned to this session'
        }, status=status.HTTP_400_BAD_REQUEST)

    # Add participant
    try:
        participant = session.add_participant(student)
        print(f"Debug: Successfully added participant {participant.id} for session {session.id}")

        return Response({
            'success': True,
            'message': f'Added {student.name} to the session',
            'participant_id': participant.id
        })
    except Exception as e:
        return Response({
            'error': f'Error adding participant: {str(e)}'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['DELETE'])
@permission_classes([permissions.IsAuthenticated])
def remove_session_participant(request, session_id, participant_id):
    """Remove participant from session (Admin only)"""
    if request.user.role != 'admin':
        return Response({
            'error': 'Admin access required'
        }, status=status.HTTP_403_FORBIDDEN)

    session = get_object_or_404(LiveSession, id=session_id)
    participant = get_object_or_404(
        SessionParticipant,
        id=participant_id,
        session=session
    )

    student_name = participant.student.name
    participant.delete()

    return Response({
        'success': True,
        'message': f'Removed {student_name} from the session'
    })


@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def session_announcements(request, session_id):
    """Get session announcements"""
    session = get_object_or_404(LiveSession, id=session_id)

    # Check if user has access to this session
    if request.user.role != 'admin':
        if not session.participants.filter(student=request.user).exists():
            return Response({
                'error': 'Access denied'
            }, status=status.HTTP_403_FORBIDDEN)

    announcements = session.announcements.select_related('created_by').order_by('-created_at')
    serializer = SessionAnnouncementSerializer(announcements, many=True)

    return Response({
        'announcements': serializer.data
    })


@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def dashboard_stats(request):
    """Get dashboard statistics for live sessions (Admin only)"""
    if request.user.role != 'admin':
        return Response({
            'error': 'Admin access required'
        }, status=status.HTTP_403_FORBIDDEN)

    total_sessions = LiveSession.objects.count()
    upcoming_sessions = LiveSession.objects.filter(
        status='scheduled',
        scheduled_date__gt=timezone.now()
    ).count()
    live_sessions = LiveSession.objects.filter(status='live').count()
    completed_sessions = LiveSession.objects.filter(status='ended').count()

    return Response({
        'total_sessions': total_sessions,
        'upcoming_sessions': upcoming_sessions,
        'live_sessions': live_sessions,
        'completed_sessions': completed_sessions,
    })