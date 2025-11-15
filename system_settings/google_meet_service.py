"""
Google Calendar and Meet API Service
Handles creation, update, and deletion of Google Meet sessions
"""
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from datetime import datetime, timedelta
from django.utils import timezone
from .google_oauth import GoogleOAuthService
from .models import GoogleMeetSession


class GoogleMeetService:
    """Service for managing Google Meet sessions via Calendar API"""

    def __init__(self, user):
        self.user = user
        self.oauth_service = GoogleOAuthService()
        self.credentials = self.oauth_service.get_credentials_for_user(user)

        if not self.credentials:
            raise ValueError("User not connected to Google Workspace")

        self.service = build('calendar', 'v3', credentials=self.credentials)

    def create_meet_session(self, live_session):
        """
        Create a Google Calendar event with Google Meet link

        Args:
            live_session: LiveSession instance

        Returns:
            GoogleMeetSession instance or None
        """
        try:
            # Calculate end time
            start_time = live_session.scheduled_date
            end_time = start_time + timedelta(minutes=live_session.duration_minutes)

            # Prepare event
            event = {
                'summary': live_session.title,
                'description': live_session.description or '',
                'start': {
                    'dateTime': start_time.isoformat(),
                    'timeZone': 'UTC',
                },
                'end': {
                    'dateTime': end_time.isoformat(),
                    'timeZone': 'UTC',
                },
                'conferenceData': {
                    'createRequest': {
                        'requestId': f'meet-{live_session.id}-{int(datetime.now().timestamp())}',
                        'conferenceSolutionKey': {
                            'type': 'hangoutsMeet'
                        },
                    }
                },
                'attendees': self._get_attendees(live_session),
                'reminders': {
                    'useDefault': False,
                    'overrides': [
                        {'method': 'email', 'minutes': 24 * 60},  # 1 day before
                        {'method': 'popup', 'minutes': 30},       # 30 min before
                    ],
                },
            }

            # Create the event
            created_event = self.service.events().insert(
                calendarId='primary',
                body=event,
                conferenceDataVersion=1,  # Required for Meet link
                sendUpdates='all' if live_session.send_notifications else 'none'
            ).execute()

            # Extract Meet information
            meet_link = created_event.get('hangoutLink', '')
            conference_data = created_event.get('conferenceData', {})
            entry_points = conference_data.get('entryPoints', [])

            # Get meeting code from entry points
            meet_code = ''
            for entry in entry_points:
                if entry.get('entryPointType') == 'video':
                    uri = entry.get('uri', '')
                    # Extract code from URI (e.g., https://meet.google.com/abc-defg-hij)
                    if 'meet.google.com/' in uri:
                        meet_code = uri.split('meet.google.com/')[-1]
                    break

            # Create GoogleMeetSession record
            google_meet_session = GoogleMeetSession.objects.create(
                live_session=live_session,
                google_event_id=created_event['id'],
                google_meet_code=meet_code,
                calendar_link=created_event.get('htmlLink', ''),
                hangout_link=meet_link,
                recording_enabled=live_session.allow_recording,
                created_by=self.user
            )

            # Update live_session with Meet link
            live_session.meeting_link = meet_link
            live_session.save(update_fields=['meeting_link'])

            return google_meet_session

        except HttpError as e:
            print(f"Google Calendar API error: {e}")
            return None
        except Exception as e:
            print(f"Error creating Google Meet session: {e}")
            return None

    def update_meet_session(self, live_session):
        """
        Update existing Google Calendar event

        Args:
            live_session: LiveSession instance with google_meet_info relation

        Returns:
            bool: Success status
        """
        try:
            google_meet = live_session.google_meet_info

            # Calculate end time
            start_time = live_session.scheduled_date
            end_time = start_time + timedelta(minutes=live_session.duration_minutes)

            # Get existing event
            event = self.service.events().get(
                calendarId='primary',
                eventId=google_meet.google_event_id
            ).execute()

            # Update event details
            event['summary'] = live_session.title
            event['description'] = live_session.description or ''
            event['start'] = {
                'dateTime': start_time.isoformat(),
                'timeZone': 'UTC',
            }
            event['end'] = {
                'dateTime': end_time.isoformat(),
                'timeZone': 'UTC',
            }
            event['attendees'] = self._get_attendees(live_session)

            # Update the event
            updated_event = self.service.events().update(
                calendarId='primary',
                eventId=google_meet.google_event_id,
                body=event,
                sendUpdates='all' if live_session.send_notifications else 'none'
            ).execute()

            return True

        except HttpError as e:
            print(f"Google Calendar API error: {e}")
            return False
        except Exception as e:
            print(f"Error updating Google Meet session: {e}")
            return False

    def cancel_meet_session(self, live_session, send_notifications=True):
        """
        Cancel/Delete Google Calendar event

        Args:
            live_session: LiveSession instance with google_meet_info relation
            send_notifications: Send cancellation emails to attendees

        Returns:
            bool: Success status
        """
        try:
            google_meet = live_session.google_meet_info

            # Delete the event
            self.service.events().delete(
                calendarId='primary',
                eventId=google_meet.google_event_id,
                sendUpdates='all' if send_notifications else 'none'
            ).execute()

            return True

        except HttpError as e:
            print(f"Google Calendar API error: {e}")
            return False
        except Exception as e:
            print(f"Error cancelling Google Meet session: {e}")
            return False

    def get_meeting_recordings(self, google_meet_session):
        """
        Get recordings for a Google Meet session (if available)
        Note: This requires Google Workspace Enterprise or higher

        Args:
            google_meet_session: GoogleMeetSession instance

        Returns:
            list: Recording URLs
        """
        # Note: Google Meet recordings are stored in Google Drive
        # This would require Drive API and proper permissions
        # For now, return empty list
        # TODO: Implement when Drive API access is configured
        return []

    def _get_attendees(self, live_session):
        """
        Get list of attendees for the session

        Args:
            live_session: LiveSession instance

        Returns:
            list: Attendee dictionaries for Google Calendar
        """
        attendees = []

        # Get all participants
        participants = live_session.participants.select_related('student').all()

        for participant in participants:
            if participant.student.email:
                attendees.append({
                    'email': participant.student.email,
                    'displayName': participant.student.get_full_name(),
                    'optional': not live_session.is_mandatory,
                })

        return attendees

    def add_attendee(self, live_session, user_email, user_name=None):
        """
        Add a single attendee to existing Google Meet

        Args:
            live_session: LiveSession instance
            user_email: Email of attendee to add
            user_name: Name of attendee (optional)

        Returns:
            bool: Success status
        """
        try:
            google_meet = live_session.google_meet_info

            # Get existing event
            event = self.service.events().get(
                calendarId='primary',
                eventId=google_meet.google_event_id
            ).execute()

            # Add new attendee
            attendees = event.get('attendees', [])
            attendees.append({
                'email': user_email,
                'displayName': user_name or user_email,
                'optional': not live_session.is_mandatory,
            })

            event['attendees'] = attendees

            # Update the event
            self.service.events().update(
                calendarId='primary',
                eventId=google_meet.google_event_id,
                body=event,
                sendUpdates='all' if live_session.send_notifications else 'none'
            ).execute()

            return True

        except Exception as e:
            print(f"Error adding attendee: {e}")
            return False

    def remove_attendee(self, live_session, user_email):
        """
        Remove an attendee from Google Meet

        Args:
            live_session: LiveSession instance
            user_email: Email of attendee to remove

        Returns:
            bool: Success status
        """
        try:
            google_meet = live_session.google_meet_info

            # Get existing event
            event = self.service.events().get(
                calendarId='primary',
                eventId=google_meet.google_event_id
            ).execute()

            # Remove attendee
            attendees = event.get('attendees', [])
            attendees = [a for a in attendees if a.get('email') != user_email]

            event['attendees'] = attendees

            # Update the event
            self.service.events().update(
                calendarId='primary',
                eventId=google_meet.google_event_id,
                body=event,
                sendUpdates='all'
            ).execute()

            return True

        except Exception as e:
            print(f"Error removing attendee: {e}")
            return False
