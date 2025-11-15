# Lyceum LMS - Complete API Documentation

**Version:** 2.0  
**Last Updated:** January 2025  
**Base URL:** `https://yourdomain.com/api/`  
**Authentication:** JWT (JSON Web Tokens)

---

## 📋 Table of Contents

1. [Authentication](#authentication)
2. [User Management](#user-management)
3. [Courses (Multi-Level Content)](#courses-multi-level-content)
4. [Enrollment & Payments](#enrollment--payments)
5. [Assignments](#assignments)
6. [Quizzes](#quizzes)
7. [Progress Tracking](#progress-tracking)
8. [Live Sessions](#live-sessions)
9. [Notifications](#notifications)
10. [Teams](#teams)
11. [Google Meet Integration (Planned)](#google-meet-integration-planned)

---

## Authentication

### Login
`POST /api/users/auth/login/`

**Request:**
```json
{
  "email": "student@example.com",
  "password": "password123"
}
```

**Response (200):**
```json
{
  "access": "eyJ0eXAiOiJKV1Qi...",
  "refresh": "eyJ0eXAiOiJKV1Qi..."
}
```

### Register
`POST /api/users/auth/register/`

**Request:**
```json
{
  "email": "new@example.com",
  "name": "John Doe",
  "password": "password123",
  "password_confirm": "password123",
  "phone_number": "+1234567890",
  "address": "123 Main St"
}
```

**Response (201):**
```json
{
  "message": "User registered successfully",
  "user": {
    "id": 1,
    "email": "new@example.com",
    "name": "John Doe",
    "role": "student"
  }
}
```

### Refresh Token
`POST /api/users/auth/refresh/`

### Password Reset
`POST /api/users/auth/password-reset/` - Request code  
`POST /api/users/auth/password-reset-with-code/` - Reset with code

---

## User Management

### Get Profile
`GET /api/users/profile/`

**Response (200):**
```json
{
  "id": 1,
  "email": "student@example.com",
  "name": "John Doe",
  "role": "student",
  "phone_number": "+1234567890",
  "address": "123 Main St",
  "date_joined": "2025-01-15T10:30:00Z"
}
```

### Update Profile
`PUT /api/users/profile/`

### Change Password
`POST /api/users/profile/change-password/`

### Delete Account
`DELETE /api/users/profile/delete-account/`

---

## Courses (Multi-Level Content)

### List Categories
`GET /api/courses/categories/`

### List Courses
`GET /api/courses/?category={id}&is_free={bool}&search={query}`

### Get Course Detail
`GET /api/courses/{id}/`

**Response includes multi-level content:**
```json
{
  "id": 1,
  "title": "Python Development",
  "assignments": [...],  // Course-level assignments
  "quizzes": [...],      // Course-level quizzes
  "pdf_notes": [...],    // Course-level PDFs
  "modules": [
    {
      "id": 1,
      "title": "Module 1",
      "assignments": [...],  // Module-level assignments
      "quizzes": [...],      // Module-level quizzes
      "pdf_notes": [...],    // Module-level PDFs
      "video_lessons": [
        {
          "id": 1,
          "title": "Lesson 1",
          "assignments": [...],  // Video-level assignments
          "quizzes": [...],      // Video-level quizzes
          "pdf_notes": [...]     // Video-level PDFs
        }
      ]
    }
  ]
}
```

### Search Courses
`GET /api/courses/search/?q={query}`

### Get Enrolled Courses
`GET /api/courses/enrolled/`

---

## Enrollment & Payments

### Get Course Pricing
`GET /api/payments/courses/{course_id}/pricing/`

### Purchase Course
`POST /api/payments/enroll/`

**Request:**
```json
{
  "course_id": 1,
  "payment_method": "razorpay",
  "transaction_id": "txn_abc123",
  "payment_gateway_response": {...}
}
```

**Response (201):**
```json
{
  "message": "Course purchased successfully",
  "enrollment_id": 1,
  "payment_id": 1,
  "total_amount": 5898.82,
  "payment_status": "completed"
}
```

### Get Enrollments
`GET /api/payments/enrollments/`

### Get Payment History
`GET /api/payments/enrollments/{id}/history/`

---

## Assignments

### Get Module Assignments
`GET /api/courses/modules/{module_id}/assignments/`

### Get Assignment Detail
`GET /api/courses/assignments/{id}/`

### Submit Assignment
`POST /api/courses/assignment-submissions/`

**Request:**
```json
{
  "assignment": 1,
  "github_url": "https://github.com/user/project"
}
```

### Get User Submissions
`GET /api/courses/assignment-submissions/`

### Submit for Review
`PATCH /api/courses/assignment-submissions/{id}/`

---

## Quizzes

### Get Module Quizzes
`GET /api/courses/modules/{module_id}/quizzes/`

### Get Quiz Detail
`GET /api/courses/quizzes/{id}/`

### Start Quiz Attempt
`POST /api/courses/quizzes/{id}/start/`

### Submit Quiz
`POST /api/courses/quiz-attempts/{attempt_id}/submit/`

**Request:**
```json
{
  "answers": [
    {"question": 1, "selected_choice": 1},
    {"question": 2, "selected_choice": 3}
  ]
}
```

### Get Quiz Attempts
`GET /api/courses/quiz-attempts/`

---

## Progress Tracking

### Get Video Progress
`GET /api/courses/progress/?course_id={id}`

### Update Video Progress
`POST /api/courses/progress/`

**Request:**
```json
{
  "video_lesson_id": 1,
  "course_id": 1,
  "completed_percentage": 85.0,
  "completed": false
}
```

### Get Module Progress
`GET /api/courses/module-progress/?course_id={id}`

---

## Live Sessions

### Student Endpoints

#### List My Sessions
`GET /api/live-sessions/`

**Response (200):**
```json
[
  {
    "id": 1,
    "title": "Python Workshop",
    "meeting_link": "https://meet.google.com/abc-defg-hij",
    "scheduled_date": "2025-01-25T15:00:00Z",
    "duration_minutes": 90,
    "status": "scheduled",
    "is_mandatory": true,
    "my_participation": {
      "status": "assigned"
    },
    "is_upcoming": true,
    "is_live_now": false,
    "time_until_session": 120,
    "can_join": false
  }
]
```

#### Get Session Detail
`GET /api/live-sessions/{id}/`

#### Join/Leave Session
`POST /api/live-sessions/{id}/join-leave/`

**Request:**
```json
{
  "action": "join"
}
```

**Response (200):**
```json
{
  "success": true,
  "message": "Successfully joined the session",
  "meeting_link": "https://meet.google.com/abc-defg-hij"
}
```

#### Get Upcoming Sessions
`GET /api/live-sessions/my-upcoming/`

#### Get Session Announcements
`GET /api/live-sessions/{id}/announcements/`

### Admin Endpoints

#### List All Sessions
`GET /api/live-sessions/admin/?status={status}&course={id}&search={query}`

#### Create Session
`POST /api/live-sessions/admin/`

**Request:**
```json
{
  "title": "Python Workshop",
  "description": "Hands-on session",
  "meeting_link": "https://meet.google.com/abc-defg-hij",
  "course": 1,
  "scheduled_date": "2025-01-25T15:00:00Z",
  "duration_minutes": 90,
  "assignment_type": "course",
  "max_participants": 50,
  "send_notifications": true,
  "allow_recording": true,
  "is_mandatory": true
}
```

#### Get Session Detail
`GET /api/live-sessions/admin/{id}/`

#### Update Session
`PUT /api/live-sessions/admin/{id}/`

#### Delete Session
`DELETE /api/live-sessions/admin/{id}/`

#### Update Session Status
`POST /api/live-sessions/admin/{id}/status/`

**Request:**
```json
{
  "action": "start"  // or "end", "cancel"
}
```

#### Get Participants
`GET /api/live-sessions/admin/{id}/participants/`

#### Add Participant
`POST /api/live-sessions/admin/{id}/participants/add/`

**Request:**
```json
{
  "student_id": 5
}
```

#### Remove Participant
`DELETE /api/live-sessions/admin/{id}/participants/{participant_id}/remove/`

#### Bulk Assign Participants
`POST /api/live-sessions/admin/{id}/bulk-assign/`

**Assign Course Students:**
```json
{
  "assignment_type": "course_students",
  "course": 1
}
```

**Assign Team:**
```json
{
  "assignment_type": "team_members",
  "team": 1
}
```

**Assign Individual:**
```json
{
  "assignment_type": "individual_students",
  "students": [1, 2, 3, 4, 5]
}
```

#### Get Dashboard Stats
`GET /api/live-sessions/admin/dashboard-stats/`

---

## Notifications

### List Notifications
`GET /api/notifications/`

### Mark as Read
`POST /api/notifications/{id}/read/`

### Mark All Read
`POST /api/notifications/mark-all-read/`

### Register Device
`POST /api/notifications/register-device/`

**Request:**
```json
{
  "fcm_token": "fcm_token_from_firebase",
  "device_type": "android",
  "device_name": "Samsung Galaxy S21"
}
```

### Link Device
`POST /api/notifications/link-device/`

### Unregister Device
`POST /api/notifications/unregister-device/`

### Device Status
`GET /api/notifications/device-status/`

---

## Teams

### List Teams
`GET /api/users/teams/`

### Create Team
`POST /api/users/teams/`

**Request:**
```json
{
  "name": "Python Developers",
  "description": "Team for Python course",
  "team_leader": 2,
  "max_members": 5,
  "member_ids": [2, 3, 4]
}
```

### Get Team Detail
`GET /api/users/teams/{id}/`

### Update Team
`PUT /api/users/teams/{id}/`

### Delete Team
`DELETE /api/users/teams/{id}/`

### Join Team
`POST /api/users/teams/{id}/join/`

### Leave Team
`POST /api/users/teams/{id}/leave/`

### Get My Teams
`GET /api/users/my-teams/`

---

## Google Meet Integration (Planned)

### 🎯 Overview
Google Meet integration will enable admins to create and manage Google Meet meetings directly from the dashboard with automatic meeting links and calendar integration.

### 📋 Planned Features

#### Admin Features
1. **Meeting Creation**
   - One-click Google Meet creation
   - Auto-generate meeting links
   - Automatic calendar invites
   - Set meeting date/time/duration
   - Add participants automatically

2. **Meeting Management**
   - Edit meeting details
   - Add/remove participants
   - Cancel with notifications
   - Reschedule meetings
   - View recordings (if enabled)

3. **Settings Configuration**
   - Connect Google Workspace account
   - OAuth2 authentication
   - Default meeting settings
   - Recording preferences
   - Waiting room options

#### Student Features
1. **Meeting Access**
   - View meeting details
   - One-click join from mobile app
   - One-click join from web dashboard
   - Calendar integration
   - Pre-meeting reminders
   - See attendees list

2. **Meeting Experience**
   - Deep links to Google Meet app
   - Meeting countdown timer
   - Notification 15 mins before
   - Post-meeting feedback

### 🚀 Planned API Endpoints

#### Create Google Meet (Admin)
`POST /api/live-sessions/admin/create-google-meet/`

**Request:**
```json
{
  "session_id": 1,
  "title": "Python Workshop",
  "scheduled_date": "2025-01-25T15:00:00Z",
  "duration_minutes": 90,
  "auto_assign_participants": true,
  "send_calendar_invites": true,
  "enable_recording": true,
  "enable_waiting_room": true
}
```

**Response:**
```json
{
  "success": true,
  "meeting_link": "https://meet.google.com/abc-defg-hij",
  "meeting_id": "abc-defg-hij",
  "calendar_event_id": "event_123",
  "participants_invited": 25
}
```

#### Get Meeting Details
`GET /api/live-sessions/{id}/google-meet-details/`

**Response:**
```json
{
  "meeting_link": "https://meet.google.com/abc-defg-hij",
  "meeting_id": "abc-defg-hij",
  "status": "scheduled",
  "can_join": false,
  "join_available_at": "2025-01-25T14:45:00Z",
  "calendar_event_link": "https://calendar.google.com/event?eid=...",
  "recording_enabled": true,
  "waiting_room_enabled": true
}
```

#### Update Meeting
`PUT /api/live-sessions/admin/{id}/update-google-meet/`

#### Cancel Meeting
`POST /api/live-sessions/admin/{id}/cancel-google-meet/`

#### Configure Settings
`POST /api/admin/google-meet-settings/`

**Request:**
```json
{
  "google_workspace_email": "admin@lyceum.academy",
  "default_duration_minutes": 90,
  "auto_recording": true,
  "waiting_room_enabled": true,
  "allow_external_participants": false,
  "send_calendar_invites": true,
  "reminder_minutes_before": 15
}
```

### 💰 Google Workspace Requirements

**Required Plan:** Google Workspace Business Standard or higher
- **Cost:** $12/user/month
- **Features:**
  - Up to 150 participants
  - Recording to Google Drive
  - Breakout rooms
  - Meeting recordings
  - Calendar API access
  - Google Meet API access

**Alternative:** Business Plus ($18/user/month)
- Up to 500 participants
- Enhanced security features
- Advanced admin controls

### 🔧 Technical Implementation

#### Required Google APIs
- Google Calendar API
- Google Meet API
- Google OAuth2 API

#### Backend Requirements
- Google API Python Client library
- OAuth2 flow implementation
- Token refresh mechanism
- Webhook handlers for events

#### Database Changes
- Add `google_meet_id` to LiveSession model
- Add `google_calendar_event_id` field
- Create GoogleMeetSettings model
- Store recording URLs

### 📱 Mobile App Integration

#### Android Deep Link
```dart
void joinGoogleMeet(String meetingLink) {
  // Try to open in Google Meet app
  launch('intent://meet.google.com/abc-defg-hij#Intent;'
         'scheme=https;package=com.google.android.apps.meetings;end');
}
```

#### iOS URL Scheme
```dart
void joinGoogleMeet(String meetingLink) {
  launch(meetingLink); // Opens in Meet app if installed
}
```

### 🌐 Web Dashboard Integration

#### Join Button
```html
<button 
  onclick="window.open('{{meeting_link}}', '_blank')"
  class="btn-join-meeting">
  Join Google Meet
</button>
```

#### Add to Calendar
```javascript
function addToCalendar(event) {
  const url = `https://calendar.google.com/calendar/render?action=TEMPLATE
    &text=${encodeURIComponent(event.title)}
    &dates=${event.startTime}/${event.endTime}
    &details=${encodeURIComponent(event.description)}
    &location=${encodeURIComponent(event.meetingLink)}`;
  window.open(url, '_blank');
}
```

### ✅ Implementation Timeline
- **Phase 1 (Week 1-2):** Google Workspace setup and OAuth configuration
- **Phase 2 (Week 3-4):** Backend API implementation
- **Phase 3 (Week 5):** Admin dashboard integration
- **Phase 4 (Week 6):** Mobile app integration
- **Phase 5 (Week 7):** Web dashboard integration
- **Phase 6 (Week 8):** Testing and deployment

---

## 📊 Error Handling

### HTTP Status Codes
- `200` OK
- `201` Created
- `204` No Content
- `400` Bad Request
- `401` Unauthorized
- `403` Forbidden
- `404` Not Found
- `500` Internal Server Error

### Error Format
```json
{
  "error": "Error message"
}
```

### Validation Errors
```json
{
  "field_name": ["Error message for field"]
}
```

---

## 🔐 Authentication

### JWT Headers
```
Authorization: Bearer eyJ0eXAiOiJKV1Qi...
```

### Token Expiration
- **Access Token:** 1 hour
- **Refresh Token:** 7 days

Use refresh endpoint when access token expires.

---

## 📄 Pagination

Query Parameters:
- `page` - Page number (default: 1)
- `page_size` - Items per page (default: 20, max: 100)

Example:
```
GET /api/courses/?page=2&page_size=50
```

---

## 🎯 Rate Limiting

- Standard endpoints: 100 requests/minute
- Authentication: 10 requests/minute
- Payments: 20 requests/minute

---

## 📞 Support

**Email:** support@lyceum.academy  
**Docs:** https://docs.lyceum.academy  
**Status:** https://status.lyceum.academy

---

**Last Updated:** January 2025  
**Version:** 2.0.0
