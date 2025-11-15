# Implementation Plan: Encrypted Settings & Google Meet Integration

## Part 1: Encrypted Settings Management in Database

### Why This is Needed
- **Security**: Store sensitive credentials encrypted in database instead of .env files
- **Flexibility**: Update settings from admin dashboard without redeploying
- **Audit Trail**: Track who changed what and when
- **Multi-Environment**: Different settings per environment without code changes

### Features to Implement

#### 1. Database Settings Model
```python
class SystemSetting(models.Model):
    """Encrypted system settings stored in database"""
    key = models.CharField(max_length=255, unique=True)
    value = EncryptedTextField()  # Encrypted field
    category = models.CharField(max_length=50)
    description = models.TextField()
    is_sensitive = models.BooleanField(default=True)
    last_updated = models.DateTimeField(auto_now=True)
    updated_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
```

#### 2. Settings Categories
- **Email Settings**: SMTP credentials, from email
- **Payment Gateway**: Razorpay keys, webhook secrets
- **Google Services**: OAuth credentials, API keys
- **Firebase**: FCM server key, project credentials
- **Security**: Secret keys, JWT secrets
- **Storage**: AWS S3, media storage credentials
- **SMS**: Twilio credentials
- **General**: Site name, logo URL, support email

#### 3. Admin Interface Features
- View all settings by category
- Edit settings with validation
- Mask sensitive values (show *****)
- Test connection buttons (test email, test payment gateway)
- Export/Import settings (encrypted)
- Audit log for changes
- Role-based access (only superadmin can change payment keys)

#### 4. Encryption Implementation
```python
from cryptography.fernet import Fernet
from django.conf import settings
import base64

class EncryptionService:
    @staticmethod
    def get_cipher():
        # Use Django SECRET_KEY or separate encryption key
        key = settings.ENCRYPTION_KEY.encode()
        return Fernet(key)

    @staticmethod
    def encrypt(value: str) -> str:
        cipher = EncryptionService.get_cipher()
        return cipher.encrypt(value.encode()).decode()

    @staticmethod
    def decrypt(value: str) -> str:
        cipher = EncryptionService.get_cipher()
        return cipher.decrypt(value.encode()).decode()
```

#### 5. Settings Usage in Code
```python
from apps.system_settings.utils import get_setting

# Old way
EMAIL_HOST = os.getenv('EMAIL_HOST')

# New way
EMAIL_HOST = get_setting('EMAIL_HOST', default='smtp.gmail.com')
```

### Implementation Steps

**Step 1:** Create `system_settings` app
```bash
python manage.py startapp system_settings
```

**Step 2:** Install required packages
```bash
pip install cryptography django-encrypted-model-fields
```

**Step 3:** Create models and migrations

**Step 4:** Build admin interface with custom views

**Step 5:** Create management command to migrate .env to DB
```bash
python manage.py migrate_env_to_db
```

**Step 6:** Update codebase to use DB settings with .env fallback

---

## Part 2: Google Meet Integration

### Overview
Full Google Meet integration with meeting creation, participant management, and calendar scheduling from admin dashboard.

### Prerequisites

#### 1. Google Workspace Account Required
- **Plan Needed:** Business Standard ($12/user/month) or higher
- **Why:** Google Meet API is only available with Google Workspace
- **Features Included:**
  - Up to 150 participants
  - Meeting recordings
  - Calendar API access
  - Meet API access

#### 2. Google Cloud Project Setup
1. Create project at https://console.cloud.google.com
2. Enable APIs:
   - Google Calendar API
   - Google People API (for participant management)
3. Create OAuth 2.0 credentials
4. Configure consent screen
5. Add authorized redirect URIs

### Features to Implement

#### 1. OAuth 2.0 Authentication Flow
```python
# Admin connects their Google Workspace account
# Store refresh token in database (encrypted)
# Auto-refresh access token when expired
```

#### 2. Meeting Creation from Admin Dashboard
- **UI Form:**
  - Session title
  - Description
  - Date & time picker
  - Duration
  - Course selection
  - Auto-assign participants option
  - Recording preferences
  - Waiting room settings

- **Backend Process:**
  1. Create Google Calendar event with Meet link
  2. Add participants to event
  3. Send calendar invites
  4. Store meeting ID and link in LiveSession
  5. Send notifications to students

#### 3. Participant Management
- Add students manually
- Auto-add from course enrollment
- Auto-add from team membership
- Remove participants
- Update attendee list

#### 4. Calendar Integration
- Create calendar events
- Send invites via email
- Update events (reschedule)
- Cancel events with notifications
- Add to user's personal calendar

#### 5. Meeting Controls
- Start meeting (opens in new tab)
- End meeting
- View attendance (who joined)
- Access recordings (if enabled)
- Meeting analytics

### Database Models

```python
class GoogleWorkspaceIntegration(models.Model):
    """Store Google Workspace OAuth credentials"""
    admin_user = models.OneToOneField(User, on_delete=models.CASCADE)
    google_email = models.EmailField()
    access_token = EncryptedTextField()
    refresh_token = EncryptedTextField()
    token_expires_at = models.DateTimeField()
    is_active = models.BooleanField(default=True)
    connected_at = models.DateTimeField(auto_now_add=True)
    last_refreshed = models.DateTimeField(auto_now=True)

class GoogleMeetSession(models.Model):
    """Extended info for Google Meet sessions"""
    live_session = models.OneToOneField(LiveSession, on_delete=models.CASCADE, related_name='google_meet_info')
    google_event_id = models.CharField(max_length=255)
    google_meet_code = models.CharField(max_length=50)  # abc-defg-hij
    calendar_link = models.URLField()
    hangout_link = models.URLField()  # Google Meet link
    recording_enabled = models.BooleanField(default=False)
    waiting_room_enabled = models.BooleanField(default=True)
    recording_urls = models.JSONField(default=list, blank=True)  # List of recording URLs
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
```

### API Implementation

```python
from googleapiclient.discovery import build
from google.oauth2.credentials import Credentials

class GoogleMeetService:
    """Service class for Google Meet operations"""

    def __init__(self, integration: GoogleWorkspaceIntegration):
        self.integration = integration
        self.credentials = self._get_credentials()
        self.calendar_service = build('calendar', 'v3', credentials=self.credentials)

    def create_meeting(self, session: LiveSession, participants: list) -> GoogleMeetSession:
        """
        Create Google Meet meeting with calendar event

        Args:
            session: LiveSession instance
            participants: List of email addresses

        Returns:
            GoogleMeetSession instance with meeting details
        """
        event = {
            'summary': session.title,
            'description': session.description,
            'start': {
                'dateTime': session.scheduled_date.isoformat(),
                'timeZone': 'Asia/Kolkata',
            },
            'end': {
                'dateTime': (session.scheduled_date + timedelta(minutes=session.duration_minutes)).isoformat(),
                'timeZone': 'Asia/Kolkata',
            },
            'attendees': [{'email': email} for email in participants],
            'conferenceData': {
                'createRequest': {
                    'requestId': f"meet-{session.id}-{uuid.uuid4().hex[:8]}",
                    'conferenceSolutionKey': {'type': 'hangoutsMeet'}
                }
            },
            'reminders': {
                'useDefault': False,
                'overrides': [
                    {'method': 'email', 'minutes': 24 * 60},
                    {'method': 'popup', 'minutes': 15},
                ],
            },
        }

        # Create event
        created_event = self.calendar_service.events().insert(
            calendarId='primary',
            body=event,
            conferenceDataVersion=1,
            sendUpdates='all'  # Send invites to all attendees
        ).execute()

        # Extract Google Meet details
        meet_link = created_event['hangoutLink']
        meet_code = meet_link.split('/')[-1]

        # Update LiveSession with meeting link
        session.meeting_link = meet_link
        session.save()

        # Create GoogleMeetSession record
        google_meet = GoogleMeetSession.objects.create(
            live_session=session,
            google_event_id=created_event['id'],
            google_meet_code=meet_code,
            calendar_link=created_event['htmlLink'],
            hangout_link=meet_link,
            recording_enabled=session.allow_recording,
            waiting_room_enabled=True
        )

        return google_meet

    def update_meeting(self, google_meet: GoogleMeetSession, **kwargs):
        """Update existing meeting"""
        event = self.calendar_service.events().get(
            calendarId='primary',
            eventId=google_meet.google_event_id
        ).execute()

        # Update fields
        if 'title' in kwargs:
            event['summary'] = kwargs['title']
        if 'description' in kwargs:
            event['description'] = kwargs['description']
        if 'scheduled_date' in kwargs:
            event['start']['dateTime'] = kwargs['scheduled_date'].isoformat()
        if 'participants' in kwargs:
            event['attendees'] = [{'email': email} for email in kwargs['participants']]

        # Update event
        updated_event = self.calendar_service.events().update(
            calendarId='primary',
            eventId=google_meet.google_event_id,
            body=event,
            sendUpdates='all'
        ).execute()

        return updated_event

    def cancel_meeting(self, google_meet: GoogleMeetSession, notify=True):
        """Cancel meeting and optionally notify participants"""
        self.calendar_service.events().delete(
            calendarId='primary',
            eventId=google_meet.google_event_id,
            sendUpdates='all' if notify else 'none'
        ).execute()

    def add_participants(self, google_meet: GoogleMeetSession, emails: list):
        """Add participants to existing meeting"""
        event = self.calendar_service.events().get(
            calendarId='primary',
            eventId=google_meet.google_event_id
        ).execute()

        # Add new attendees
        existing_emails = {a['email'] for a in event.get('attendees', [])}
        new_attendees = [{'email': email} for email in emails if email not in existing_emails]

        if new_attendees:
            event['attendees'] = event.get('attendees', []) + new_attendees
            self.calendar_service.events().update(
                calendarId='primary',
                eventId=google_meet.google_event_id,
                body=event,
                sendUpdates='all'
            ).execute()

    def _get_credentials(self):
        """Get valid credentials (refresh if needed)"""
        from django.utils import timezone

        # Check if token expired
        if self.integration.token_expires_at <= timezone.now():
            self._refresh_token()

        creds_data = {
            'token': decrypt_value(self.integration.access_token),
            'refresh_token': decrypt_value(self.integration.refresh_token),
            'token_uri': 'https://oauth2.googleapis.com/token',
            'client_id': get_setting('GOOGLE_OAUTH_CLIENT_ID'),
            'client_secret': get_setting('GOOGLE_OAUTH_CLIENT_SECRET'),
        }

        return Credentials(**creds_data)

    def _refresh_token(self):
        """Refresh expired access token"""
        # Implementation for token refresh
        pass
```

### Admin Dashboard UI

#### 1. Google Workspace Connection Page
```html
<!-- templates/custom_admin/google_workspace/connect.html -->
<div class="card">
  <div class="card-header">
    <h3>Connect Google Workspace</h3>
  </div>
  <div class="card-body">
    {% if not is_connected %}
      <p>Connect your Google Workspace account to enable Google Meet integration.</p>
      <a href="{% url 'admin:google-oauth-start' %}" class="btn btn-primary">
        <i class="fab fa-google"></i> Connect Google Workspace
      </a>
    {% else %}
      <div class="alert alert-success">
        <i class="fas fa-check-circle"></i> Connected as {{ google_email }}
      </div>
      <button onclick="disconnectGoogle()" class="btn btn-danger">
        Disconnect
      </button>
    {% endif %}
  </div>
</div>
```

#### 2. Meeting Creation Form
```html
<!-- templates/custom_admin/live_sessions/create_google_meet.html -->
<form method="post" id="createMeetingForm">
  {% csrf_token %}

  <div class="row">
    <div class="col-md-6">
      <div class="form-group">
        <label>Session Title</label>
        <input type="text" name="title" class="form-control" required>
      </div>
    </div>

    <div class="col-md-6">
      <div class="form-group">
        <label>Course</label>
        <select name="course" class="form-control">
          <option value="">-- Select Course --</option>
          {% for course in courses %}
            <option value="{{ course.id }}">{{ course.title }}</option>
          {% endfor %}
        </select>
      </div>
    </div>
  </div>

  <div class="row">
    <div class="col-md-6">
      <div class="form-group">
        <label>Date & Time</label>
        <input type="datetime-local" name="scheduled_date" class="form-control" required>
      </div>
    </div>

    <div class="col-md-6">
      <div class="form-group">
        <label>Duration (minutes)</label>
        <input type="number" name="duration_minutes" class="form-control" value="60" required>
      </div>
    </div>
  </div>

  <div class="form-group">
    <label>Description</label>
    <textarea name="description" class="form-control" rows="3"></textarea>
  </div>

  <div class="row">
    <div class="col-md-6">
      <div class="form-check mb-3">
        <input type="checkbox" name="auto_assign_participants" id="autoAssign" class="form-check-input" checked>
        <label for="autoAssign" class="form-check-label">
          Auto-assign students from course
        </label>
      </div>
    </div>

    <div class="col-md-6">
      <div class="form-check mb-3">
        <input type="checkbox" name="enable_recording" id="recording" class="form-check-input">
        <label for="recording" class="form-check-label">
          Enable recording
        </label>
      </div>
    </div>
  </div>

  <div class="form-group">
    <label>Additional Participants (one email per line)</label>
    <textarea name="additional_emails" class="form-control" rows="3" placeholder="email1@example.com
email2@example.com"></textarea>
  </div>

  <button type="submit" class="btn btn-success">
    <i class="fab fa-google"></i> Create Google Meet
  </button>
</form>
```

### Mobile App Deep Links

#### Android
```dart
Future<void> joinGoogleMeet(String meetingLink) async {
  final meetCode = meetingLink.split('/').last;

  // Try to open in Google Meet app
  final intent = 'intent://meet.google.com/$meetCode#Intent;'
      'scheme=https;'
      'package=com.google.android.apps.meetings;'
      'end';

  if (await canLaunch(intent)) {
    await launch(intent);
  } else {
    // Fallback to browser
    await launch(meetingLink);
  }
}
```

#### iOS
```dart
Future<void> joinGoogleMeet(String meetingLink) async {
  // iOS will automatically open in Google Meet app if installed
  if (await canLaunch(meetingLink)) {
    await launch(meetingLink);
  }
}
```

### Implementation Timeline

**Week 1-2: Encrypted Settings System**
- Day 1-2: Create models and encryption service
- Day 3-4: Build admin interface
- Day 5-7: Migrate existing .env values
- Day 8-10: Update codebase to use DB settings
- Day 11-14: Testing and documentation

**Week 3-4: Google Meet Integration**
- Day 1-3: Google Cloud setup and OAuth flow
- Day 4-7: Meeting creation API
- Day 8-10: Admin UI for meeting creation
- Day 11-14: Participant management and calendar integration

**Week 5-6: Mobile & Web Integration**
- Day 1-7: Mobile app deep links and UI
- Day 8-14: Web dashboard integration and testing

### Security Considerations

1. **Encryption Key Management**
   - Store encryption key in environment variable (not in DB)
   - Use strong key generation
   - Rotate keys periodically

2. **OAuth Token Security**
   - Store refresh tokens encrypted
   - Auto-refresh access tokens
   - Implement token revocation

3. **Access Control**
   - Only superadmins can view/edit payment keys
   - Audit log for all setting changes
   - Rate limiting on OAuth endpoints

4. **Data Protection**
   - Mask sensitive values in UI
   - HTTPS only for all OAuth flows
   - Secure webhook endpoints

### Cost Estimation

**Google Workspace:**
- Business Standard: $12/user/month
- For 1 admin account: $12/month = ₹1000/month (approx)

**Additional Costs:**
- Google Cloud API calls: Free tier sufficient for most use cases
- Storage for recordings: Stored in Google Drive (15GB free per user)

**Total Monthly Cost:** ~₹1000-1500/month

### Fallback Strategy

If Google Workspace is not available:
1. Manual meeting link entry (current functionality)
2. Use free alternatives (Zoom, Jitsi, etc.)
3. Store meeting links without calendar integration

---

## Questions to Clarify

1. **Google Workspace:** Do you already have a Google Workspace account or need to create one?

2. **Priority:** Which feature should we implement first?
   - Encrypted settings management
   - Google Meet integration
   - Both in parallel

3. **Settings to Migrate:** Which settings do you want to move to database?
   - Payment gateway keys
   - Email credentials
   - Firebase credentials
   - All of the above

4. **Google Meet Usage:** Expected usage?
   - How many meetings per month?
   - How many participants per meeting?
   - Recording needed?

---

## Next Steps

Let me know your preferences and I'll start implementing:

1. **Phase 1:** Encrypted settings system
2. **Phase 2:** Google Meet integration
3. **Testing:** Both features
4. **Documentation:** Admin user guide

Both features are 100% achievable and will significantly improve your LMS!
