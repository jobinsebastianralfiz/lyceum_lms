# Timezone Configuration - Indian Standard Time (IST)

**Date:** November 15, 2025
**Status:** ✅ Configured and Working

---

## Overview

The Lyceum LMS is configured to use **Indian Standard Time (IST)** throughout the entire system - both backend (Django) and frontend (Flutter app).

---

## Backend Configuration (Django)

### Settings

**File:** `codelearn_lms/settings.py`

```python
# Internationalization
LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'Asia/Kolkata'  # Indian Standard Time (UTC+05:30)
USE_I18N = True
USE_TZ = True  # Store in UTC, display in TIME_ZONE
```

### How It Works

1. **Database Storage:** All dates are stored in UTC in the database
2. **API Response:** Django automatically converts UTC to IST when serializing dates
3. **Timezone Format:** Dates are returned with timezone offset: `2025-11-15T15:18:00+05:30`

### Example API Response

```json
{
  "scheduled_date": "2025-11-15T15:18:00+05:30",
  "created_at": "2025-09-13T14:18:00.821084+05:30"
}
```

**Breakdown:**
- `2025-11-15` - Date (November 15, 2025)
- `T15:18:00` - Time (3:18 PM)
- `+05:30` - Timezone offset (IST is UTC+5:30)

---

## Frontend Configuration (Flutter)

### Package Added

**File:** `pubspec.yaml`

```yaml
dependencies:
  intl: ^0.19.0  # For date/time formatting
```

### Date Parsing

**File:** `lib/model/notification_model.dart`

```dart
class LiveSession {
  final String scheduledDate;  // Stored as string from API

  factory LiveSession.fromJson(Map<String, dynamic> json) {
    return LiveSession(
      scheduledDate: json['scheduled_date'],  // "2025-11-15T15:18:00+05:30"
      // ... other fields
    );
  }
}
```

### Date Display

**File:** `lib/view/live_sessions_page.dart`

```dart
import 'package:intl/intl.dart';

// Parse the timezone-aware date string
final scheduledDate = DateTime.parse(session.scheduledDate);
// DateTime.parse() automatically handles the timezone offset

// Format for display
String _formatDateTime(DateTime dateTime) {
  final now = DateTime.now();
  final today = DateTime(now.year, now.month, now.day);
  final sessionDate = DateTime(dateTime.year, dateTime.month, dateTime.day);

  String dateStr;
  if (sessionDate == today) {
    dateStr = 'Today';
  } else if (sessionDate.difference(today).inDays == 1) {
    dateStr = 'Tomorrow';
  } else if (sessionDate.difference(today).inDays == -1) {
    dateStr = 'Yesterday';
  } else {
    dateStr = DateFormat('d MMM yyyy').format(dateTime);  // "15 Nov 2025"
  }

  final timeStr = DateFormat('h:mm a').format(dateTime);  // "3:18 PM"

  return '$dateStr at $timeStr IST';
}
```

### Display Examples

| API Date | Parsed DateTime | Displayed As |
|----------|----------------|--------------|
| `2025-11-15T15:18:00+05:30` | `DateTime(2025, 11, 15, 15, 18)` | "Today at 3:18 PM IST" |
| `2025-11-16T10:30:00+05:30` | `DateTime(2025, 11, 16, 10, 30)` | "Tomorrow at 10:30 AM IST" |
| `2025-11-20T14:00:00+05:30` | `DateTime(2025, 11, 20, 14, 0)` | "20 Nov 2025 at 2:00 PM IST" |

---

## Timezone Handling Flow

### Complete Flow (Backend → Frontend)

1. **Admin Creates Live Session:**
   - Enters date/time in web interface
   - Django stores in database as UTC
   - Example: User enters "3:18 PM IST" → Stored as "09:48:00 UTC"

2. **API Returns Session:**
   - Django reads UTC from database
   - Converts to IST (TIME_ZONE setting)
   - Returns: `"scheduled_date": "2025-11-15T15:18:00+05:30"`

3. **Flutter App Receives:**
   - Receives timezone-aware string
   - Parses with `DateTime.parse()`
   - Dart automatically handles the `+05:30` offset

4. **Flutter App Displays:**
   - Uses `DateFormat` for user-friendly display
   - Shows "Today at 3:18 PM IST"
   - Users see correct Indian Standard Time

---

## Benefits

✅ **Consistency:** All times displayed in IST across web and mobile
✅ **Automatic Conversion:** Django and Dart handle timezone math automatically
✅ **User-Friendly:** Displays "Today", "Tomorrow" with 12-hour format
✅ **Explicit:** Shows "IST" suffix so users know the timezone
✅ **Future-Proof:** If you expand to other countries, can easily support multiple timezones

---

## Testing

### Verify Backend Returns IST

```bash
curl -X POST http://127.0.0.1:8000/api/users/auth/login/ \
  -H "Content-Type: application/json" \
  -d '{"email":"student@example.com","password":"password123"}'

# Get token, then:
curl http://127.0.0.1:8000/api/live-sessions/my-upcoming/ \
  -H "Authorization: Bearer YOUR_TOKEN"

# Check that dates include +05:30 timezone offset
```

### Verify Flutter Displays IST

Run the Flutter app and check live session dates:
- Should show "IST" suffix
- Times should match what admin entered
- Should show "Today/Tomorrow" for near dates

---

## Important Notes

1. **Database Always UTC:** Never store dates in local timezone, always UTC
2. **API Returns IST:** All API responses include the `+05:30` offset
3. **Flutter Parses Automatically:** `DateTime.parse()` handles timezone offsets
4. **Display Shows IST:** All user-facing dates explicitly show "IST"

---

## Related Files

### Backend
- `/codelearn_lms/settings.py` - TIME_ZONE configuration
- `/apps/live_sessions/models.py` - Date fields
- `/apps/live_sessions/serializers.py` - Date serialization

### Frontend
- `/pubspec.yaml` - intl package dependency
- `/lib/model/notification_model.dart` - Date parsing from API
- `/lib/view/live_sessions_page.dart` - Date display formatting

---

**The entire system is now configured for Indian Standard Time!** 🇮🇳⏰
