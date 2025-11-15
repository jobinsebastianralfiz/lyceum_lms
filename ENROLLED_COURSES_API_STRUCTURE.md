# Enrolled Courses API - Response Structure

**Endpoint:** `GET /api/courses/enrolled/`
**Authentication:** Required (Bearer Token)
**Status:** ✅ Working (Fixed Nov 15, 2025)

---

## Response Structure

```json
{
  "count": 1,
  "next": null,
  "previous": null,
  "results": [
    {
      // COURSE BASIC INFO
      "id": 10,
      "title": "Django REST API Development",
      "description": "Course description...",
      "curriculum": "<p>HTML content</p>",
      "what_you_will_learn": "<p>HTML content</p>",

      // CATEGORY
      "category": {
        "id": 1,
        "name": "Web Development",
        "description": "Category description",
        "course_count": 7,
        "created_at": "2025-07-31T09:46:49.765489+05:30"
      },

      // PRICING
      "price": "22000.00",
      "tax_rate": "18.00",
      "price_display": "₹22000.00",
      "total_price_display": "₹25960.00",
      "is_free_course": false,

      // MEDIA
      "thumbnail": "http://localhost:8000/media/course_thumbnails/image.jpg",
      "thumbnail_url": "http://localhost:8000/media/course_thumbnails/image.jpg",
      "preview_video": "",
      "preview_video_url": null,

      // PUBLICATION
      "is_published": true,
      "allow_public_enrollment": true,
      "created_by_name": "Admin User",

      // MODULES (ordered array)
      "modules": [
        {
          "id": 2,
          "title": "Module Name",
          "order": 2,
          "lesson_count": 2,

          // VIDEO LESSONS IN MODULE
          "video_lessons": [
            {
              "id": 2,
              "title": "Lesson Title",
              "youtube_video_id": null,
              "youtube_url": "https://www.youtube.com/watch?v=...",
              "thumbnail_url": null,
              "duration": 10,
              "duration_display": "00:10",
              "description": "Lesson description",
              "order": 1,
              "is_preview": false,
              "can_access": true,
              "resource_file_url": "http://localhost:8000/media/lesson_resources/file.txt",
              "platform": "youtube",
              "video_url": null,
              "embed_url": null,
              "vimeo_video_id": null,
              "assignments": [],  // Video-level assignments
              "quizzes": [],      // Video-level quizzes
              "pdf_notes": []     // Video-level PDFs
            }
          ],

          // MODULE-LEVEL CONTENT
          "assignments": [],  // Module-level assignments
          "quizzes": [],      // Module-level quizzes
          "pdf_notes": [],    // Module-level PDFs

          // PROGRESS
          "progress": {
            "is_unlocked": false,
            "is_completed": false,
            "completion_percentage": 0.0,
            "videos_completed": 0,
            "assignments_completed": 0,
            "quizzes_passed": 0
          }
        }
      ],

      // ⭐ NEW: COURSE-LEVEL ASSIGNMENTS (ordered)
      "assignments": [
        {
          "id": 1,
          "title": "Sample Course Assignment",
          "description": "Assignment description",
          "max_points": 100,
          "passing_score": 70,
          "is_required": true,
          "order": 1,
          "due_days": 7,
          "created_at": "2025-11-15T09:37:36.780403Z"
        }
      ],

      // ⭐ NEW: COURSE-LEVEL QUIZZES (ordered)
      "quizzes": [
        {
          "id": 1,
          "title": "Test Quiz",
          "description": "Quiz description",
          "time_limit": 30,
          "passing_score": 70,
          "max_attempts": 3,
          "is_required": false,
          "order": 1,
          "total_questions": 0,
          "created_at": "2025-08-06T09:39:52.056063Z"
        }
      ],

      // ⭐ NEW: COURSE-LEVEL PDF NOTES (ordered)
      "pdf_notes": [
        {
          "id": 2,
          "title": "Course PDF",
          "description": "PDF description",
          "pdf_url": "http://localhost:8000/media/course_pdfs/file.pdf",
          "file_size": 1860041,
          "page_count": 2,
          "is_downloadable": true,
          "order": 1,
          "created_at": "2025-11-15T10:18:38.971726Z"
        }
      ],

      // ENROLLMENT
      "is_enrolled": true,
      "enrollment_info": {
        "enrolled_on": "2025-11-15T10:20:12.716759Z",
        "payment_status": "completed",
        "total_amount": 25960.0,
        "outstanding_amount": 25960.0
      },

      // STATS
      "rating": 0.0,
      "enrolled_count": 3,
      "level": "beginner",
      "duration": null,
      "created_at": "2025-08-06T15:23:26.458021+05:30"
    }
  ]
}
```

---

## Key Changes from Previous Version

### ✅ Added Course-Level Content (NEW!)

1. **`assignments` array**: Course-level assignments (independent of modules)
2. **`quizzes` array**: Course-level quizzes (independent of modules)
3. **`pdf_notes` array**: Course-level PDF notes (independent of modules)

### Content Hierarchy

```
Course
├── modules[] (ordered by 'order')
│   ├── video_lessons[] (ordered by 'order')
│   │   ├── assignments[] (video-level)
│   │   ├── quizzes[] (video-level)
│   │   └── pdf_notes[] (video-level)
│   ├── assignments[] (module-level)
│   ├── quizzes[] (module-level)
│   └── pdf_notes[] (module-level)
├── assignments[] ⭐ NEW (course-level, ordered)
├── quizzes[] ⭐ NEW (course-level, ordered)
└── pdf_notes[] ⭐ NEW (course-level, ordered)
```

---

## Field Definitions

### Assignment Fields
- `id`: Unique identifier
- `title`: Assignment name
- `description`: Assignment details
- `max_points`: Maximum score
- `passing_score`: Minimum score to pass
- `is_required`: Whether required for course completion
- `order`: Display order
- `due_days`: Number of days to complete (not `due_date`)
- `created_at`: ISO 8601 datetime

### Quiz Fields
- `id`: Unique identifier
- `title`: Quiz name
- `description`: Quiz details
- `time_limit`: Time limit in minutes
- `passing_score`: Minimum score to pass
- `max_attempts`: Maximum number of attempts
- `is_required`: Whether required for course completion
- `order`: Display order
- `total_questions`: Number of questions in quiz
- `created_at`: ISO 8601 datetime

### PDF Note Fields
- `id`: Unique identifier
- `title`: PDF name
- `description`: PDF details
- `pdf_url`: Full URL to PDF file
- `file_size`: File size in bytes
- `page_count`: Number of pages
- `is_downloadable`: Whether students can download
- `order`: Display order
- `created_at`: ISO 8601 datetime

---

## Flutter Model Updates Required

### 1. Update Course Model

Add these fields to your `Course` model:

```dart
class Course {
  // ... existing fields ...

  // NEW: Course-level content
  List<Assignment>? courseAssignments;
  List<Quiz>? courseQuizzes;
  List<PDFNote>? coursePdfNotes;

  Course.fromJson(Map<String, dynamic> json) {
    // ... existing parsing ...

    // Parse course-level assignments
    if (json['assignments'] != null) {
      courseAssignments = (json['assignments'] as List)
          .map((a) => Assignment.fromJson(a))
          .toList();
    }

    // Parse course-level quizzes
    if (json['quizzes'] != null) {
      courseQuizzes = (json['quizzes'] as List)
          .map((q) => Quiz.fromJson(q))
          .toList();
    }

    // Parse course-level PDFs
    if (json['pdf_notes'] != null) {
      coursePdfNotes = (json['pdf_notes'] as List)
          .map((p) => PDFNote.fromJson(p))
          .toList();
    }
  }
}
```

### 2. Create/Update PDFNote Model

```dart
class PDFNote {
  final int id;
  final String title;
  final String? description;
  final String? pdfUrl;
  final int? fileSize;
  final int? pageCount;
  final bool isDownloadable;
  final int order;
  final DateTime createdAt;

  PDFNote.fromJson(Map<String, dynamic> json)
    : id = json['id'],
      title = json['title'],
      description = json['description'],
      pdfUrl = json['pdf_url'],
      fileSize = json['file_size'],
      pageCount = json['page_count'],
      isDownloadable = json['is_downloadable'] ?? true,
      order = json['order'],
      createdAt = DateTime.parse(json['created_at']);
}
```

### 3. Update Assignment Model

Ensure it has `dueDays` (not `dueDate`):

```dart
class Assignment {
  // ... existing fields ...
  final int? dueDays;  // Changed from dueDate!

  Assignment.fromJson(Map<String, dynamic> json)
    : // ... existing fields ...
      dueDays = json['due_days'];
}
```

---

## UI Implementation Recommendations

### Display Order

Show content in this order:

1. **Course Overview**
2. **Course-Level Assignments** (if any)
3. **Course-Level Quizzes** (if any)
4. **Course-Level PDFs** (if any)
5. **Modules** (with their nested content)

### Example UI Structure

```
┌─────────────────────────────────────┐
│ Course: Django REST API Development│
├─────────────────────────────────────┤
│ 📝 Course Assignments (1)           │
│   • Sample Course Assignment        │
├─────────────────────────────────────┤
│ ❓ Course Quizzes (1)                │
│   • Test Quiz                       │
├─────────────────────────────────────┤
│ 📄 Course PDFs (1)                  │
│   • Course Overview PDF             │
├─────────────────────────────────────┤
│ 📚 Modules                          │
│   Module 1: Introduction            │
│     🎥 Lesson 1                     │
│     🎥 Lesson 2                     │
│   Module 2: Advanced Topics         │
│     🎥 Lesson 3                     │
│     📝 Module Assignment             │
└─────────────────────────────────────┘
```

---

## Testing

✅ **Status**: API tested and working
✅ **Login**: `jobin@ralfiz.com` / `Mkagmca021#`
✅ **Response**: Full course data with modules and course-level content
✅ **Sample Data**: Course has 1 assignment, 1 quiz, 1 PDF at course level

---

## Notes

- All `order` fields define display sequence
- Course-level content is independent of modules
- Students can access course-level content anytime
- Module-level and video-level content still work as before
- PDFs have `is_downloadable` flag to control download permission
