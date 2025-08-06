# CodeLearn LMS - Flutter API Documentation

## Base Configuration

```dart
const String BASE_URL = "https://your-domain.com/api/v1";
const String ADMIN_BASE_URL = "https://your-domain.com/admin/api/v1";
```

## Authentication

### Headers Required
```dart
Map<String, String> headers = {
  'Content-Type': 'application/json',
  'Authorization': 'Bearer ${token}', // For authenticated requests
  'Accept': 'application/json',
};
```

---

## 🔐 Authentication Endpoints

### 1. User Registration
```http
POST /auth/register/
```

**Request Body:**
```json
{
  "name": "John Doe",
  "email": "john@example.com",
  "password": "securePassword123",
  "phone_number": "+1234567890",
  "address": "123 Main St, City, Country"
}
```

**Response (201 Created):**
```json
{
  "success": true,
  "message": "User registered successfully",
  "data": {
    "user": {
      "id": 1,
      "name": "John Doe",
      "email": "john@example.com",
      "role": "student",
      "phone_number": "+1234567890",
      "address": "123 Main St, City, Country",
      "created_at": "2025-01-15T10:30:00Z"
    },
    "token": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...",
    "refresh_token": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9..."
  }
}
```

### 2. User Login
```http
POST /auth/login/
```

**Request Body:**
```json
{
  "email": "john@example.com",
  "password": "securePassword123"
}
```

**Response (200 OK):**
```json
{
  "success": true,
  "message": "Login successful",
  "data": {
    "user": {
      "id": 1,
      "name": "John Doe",
      "email": "john@example.com",
      "role": "student",
      "phone_number": "+1234567890",
      "is_staff": false
    },
    "token": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...",
    "refresh_token": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9..."
  }
}
```

### 3. Refresh Token
```http
POST /auth/refresh/
```

**Request Body:**
```json
{
  "refresh_token": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9..."
}
```

### 4. Logout
```http
POST /auth/logout/
```

---

## 👤 User Profile Endpoints

### 1. Get User Profile
```http
GET /users/profile/
```

**Response (200 OK):**
```json
{
  "success": true,
  "data": {
    "id": 1,
    "name": "John Doe",
    "email": "john@example.com",
    "role": "student",
    "phone_number": "+1234567890",
    "address": "123 Main St, City, Country",
    "created_at": "2025-01-15T10:30:00Z",
    "enrollments_count": 3,
    "completed_courses": 1
  }
}
```

### 2. Update User Profile
```http
PUT /users/profile/
```

**Request Body:**
```json
{
  "name": "John Updated",
  "phone_number": "+1234567891",
  "address": "Updated Address"
}
```

### 3. Change Password
```http
POST /users/change-password/
```

**Request Body:**
```json
{
  "current_password": "oldPassword123",
  "new_password": "newPassword456"
}
```

---

## 📚 Course Endpoints

### 1. Get All Courses (Public)
```http
GET /courses/?page=1&search=python&category=1
```

**Query Parameters:**
- `page` (optional): Page number for pagination
- `search` (optional): Search term for course title/description
- `category` (optional): Filter by category ID
- `is_free` (optional): true/false for free courses

**Response (200 OK):**
```json
{
  "success": true,
  "data": {
    "count": 25,
    "next": "http://api.example.com/courses/?page=2",
    "previous": null,
    "results": [
      {
        "id": 1,
        "title": "Python for Beginners",
        "description": "Learn Python programming from scratch",
        "category": {
          "id": 1,
          "name": "Programming"
        },
        "price": 2999.00,
        "tax_rate": 18.00,
        "total_price": 3538.82,
        "is_free": false,
        "thumbnail": "https://example.com/media/course_thumbnails/python.jpg",
        "preview_video": "https://youtube.com/watch?v=abc123",
        "is_published": true,
        "created_by": {
          "id": 2,
          "name": "Instructor Name"
        },
        "modules_count": 8,
        "total_lessons": 45,
        "total_duration": 1800,
        "enrollments_count": 150,
        "created_at": "2025-01-10T09:00:00Z"
      }
    ]
  }
}
```

### 2. Get Course Details
```http
GET /courses/{course_id}/
```

**Response (200 OK):**
```json
{
  "success": true,
  "data": {
    "id": 1,
    "title": "Python for Beginners",
    "description": "Comprehensive Python course...",
    "category": {
      "id": 1,
      "name": "Programming"
    },
    "price": 2999.00,
    "total_price": 3538.82,
    "thumbnail": "https://example.com/media/course_thumbnails/python.jpg",
    "preview_video": "https://youtube.com/watch?v=abc123",
    "modules": [
      {
        "id": 1,
        "title": "Introduction to Python",
        "order": 1,
        "lessons": [
          {
            "id": 1,
            "title": "What is Python?",
            "youtube_video_id": "dQw4w9WgXcQ",
            "duration": 600,
            "is_preview": true,
            "order": 1
          },
          {
            "id": 2,
            "title": "Installing Python",
            "youtube_video_id": "abc123def",
            "duration": 900,
            "is_preview": false,
            "order": 2
          }
        ]
      }
    ],
    "instructor": {
      "id": 2,
      "name": "Instructor Name"
    },
    "is_enrolled": false,
    "enrollment_status": null
  }
}
```

### 3. Get Course Categories
```http
GET /categories/
```

**Response (200 OK):**
```json
{
  "success": true,
  "data": [
    {
      "id": 1,
      "name": "Programming",
      "description": "Programming and software development courses",
      "courses_count": 15
    },
    {
      "id": 2,
      "name": "Design",
      "description": "UI/UX and graphic design courses",
      "courses_count": 8
    }
  ]
}
```

---

## 📝 Assignment Endpoints

### 1. Get Module Assignments
```http
GET /courses/modules/{module_id}/assignments/
```

**Response (200 OK):**
```json
{
  "success": true,
  "data": [
    {
      "id": 1,
      "title": "Python Variables Exercise",
      "description": "Create a Python script that demonstrates variable usage",
      "requirements": "Create a Python file with at least 5 different variable types",
      "resources": "https://docs.python.org/3/tutorial/introduction.html",
      "max_points": 100,
      "passing_score": 70,
      "due_days": 7,
      "is_required": true,
      "order": 1,
      "module_title": "Python Basics",
      "course_title": "Python for Beginners",
      "submission_status": "not_submitted",
      "user_submission": null,
      "created_at": "2025-01-10T09:00:00Z"
    }
  ]
}
```

### 2. Get Assignment Details
```http
GET /courses/assignments/{assignment_id}/
```

**Response (200 OK):**
```json
{
  "success": true,
  "data": {
    "id": 1,
    "title": "Python Variables Exercise",
    "description": "Create a Python script that demonstrates variable usage",
    "requirements": "Create a Python file with at least 5 different variable types",
    "resources": "https://docs.python.org/3/tutorial/introduction.html",
    "max_points": 100,
    "passing_score": 70,
    "due_days": 7,
    "is_required": true,
    "submission_status": "submitted",
    "user_submission": {
      "id": 1,
      "github_url": "https://github.com/student/python-variables",
      "submission_notes": "Completed all requirements",
      "status": "graded",
      "score": 85,
      "grade_comments": "Great work! Good variable usage examples.",
      "submitted_at": "2025-01-12T14:30:00Z",
      "graded_at": "2025-01-13T10:15:00Z"
    }
  }
}
```

### 3. Submit Assignment
```http
POST /courses/assignment-submissions/
```

**Request Body:**
```json
{
  "assignment": 1,
  "github_url": "https://github.com/student/python-variables",
  "submission_notes": "Completed all requirements as specified"
}
```

**Response (201 Created):**
```json
{
  "success": true,
  "message": "Assignment submitted successfully",
  "data": {
    "id": 1,
    "assignment": 1,
    "assignment_title": "Python Variables Exercise",
    "github_url": "https://github.com/student/python-variables",
    "submission_notes": "Completed all requirements as specified",
    "status": "draft",
    "score": null,
    "grade_comments": null,
    "submitted_at": null,
    "created_at": "2025-01-12T14:30:00Z"
  }
}
```

### 4. Submit Assignment for Review
```http
PATCH /courses/assignment-submissions/{submission_id}/
```

**Response (200 OK):**
```json
{
  "success": true,
  "message": "Assignment submitted for review",
  "data": {
    "id": 1,
    "status": "submitted",
    "submitted_at": "2025-01-12T14:30:00Z"
  }
}
```

### 5. Get My Assignment Submissions
```http
GET /courses/assignment-submissions/?assignment=1
```

**Response (200 OK):**
```json
{
  "success": true,
  "data": [
    {
      "id": 1,
      "assignment_title": "Python Variables Exercise",
      "github_url": "https://github.com/student/python-variables",
      "status": "graded",
      "score": 85,
      "score_percentage": 85.0,
      "is_passed": true,
      "grade_comments": "Great work!",
      "submitted_at": "2025-01-12T14:30:00Z",
      "graded_at": "2025-01-13T10:15:00Z"
    }
  ]
}
```

---

## 🧠 Quiz Endpoints

### 1. Get Module Quizzes
```http
GET /courses/modules/{module_id}/quizzes/
```

**Response (200 OK):**
```json
{
  "success": true,
  "data": [
    {
      "id": 1,
      "title": "Python Basics Quiz",
      "description": "Test your knowledge of Python fundamentals",
      "time_limit": 30,
      "max_attempts": 3,
      "passing_score": 70,
      "is_required": true,
      "total_questions": 10,
      "total_points": 100,
      "user_attempts": 1,
      "can_attempt": true,
      "best_score": 85.0,
      "questions": [
        {
          "id": 1,
          "question_text": "What is a variable in Python?",
          "question_type": "multiple_choice",
          "points": 10,
          "choices": [
            {
              "id": 1,
              "choice_text": "A container for storing data values",
              "order": 1
            },
            {
              "id": 2,
              "choice_text": "A type of loop",
              "order": 2
            },
            {
              "id": 3,
              "choice_text": "A function",
              "order": 3
            }
          ]
        }
      ]
    }
  ]
}
```

### 2. Get Quiz Details
```http
GET /courses/quizzes/{quiz_id}/
```

### 3. Start Quiz Attempt
```http
POST /courses/quizzes/{quiz_id}/start/
```

**Response (201 Created):**
```json
{
  "success": true,
  "message": "Quiz attempt started",
  "data": {
    "id": 1,
    "quiz_title": "Python Basics Quiz",
    "attempt_number": 2,
    "score": 0,
    "total_points": 100,
    "completed": false,
    "started_at": "2025-01-15T14:00:00Z",
    "time_limit_expires_at": "2025-01-15T14:30:00Z"
  }
}
```

### 4. Submit Quiz Answers
```http
POST /courses/quiz-attempts/{attempt_id}/submit/
```

**Request Body:**
```json
{
  "answers": [
    {
      "question": 1,
      "selected_choice": 1
    },
    {
      "question": 2,
      "selected_choice": 3
    },
    {
      "question": 3,
      "text_answer": "Variables store data"
    }
  ]
}
```

**Response (200 OK):**
```json
{
  "success": true,
  "message": "Quiz submitted successfully",
  "data": {
    "id": 1,
    "quiz_title": "Python Basics Quiz",
    "attempt_number": 2,
    "score": 85,
    "total_points": 100,
    "score_percentage": 85.0,
    "is_passed": true,
    "time_taken": 1200,
    "time_taken_display": "20m 0s",
    "completed": true,
    "completed_at": "2025-01-15T14:20:00Z"
  }
}
```

### 5. Get My Quiz Attempts
```http
GET /courses/quiz-attempts/?quiz=1
```

**Response (200 OK):**
```json
{
  "success": true,
  "data": [
    {
      "id": 1,
      "quiz_title": "Python Basics Quiz",
      "attempt_number": 1,
      "score": 75,
      "score_percentage": 75.0,
      "is_passed": true,
      "time_taken_display": "18m 30s",
      "completed": true,
      "started_at": "2025-01-14T10:00:00Z",
      "completed_at": "2025-01-14T10:18:30Z"
    },
    {
      "id": 2,
      "quiz_title": "Python Basics Quiz", 
      "attempt_number": 2,
      "score": 85,
      "score_percentage": 85.0,
      "is_passed": true,
      "time_taken_display": "20m 0s",
      "completed": true,
      "started_at": "2025-01-15T14:00:00Z",
      "completed_at": "2025-01-15T14:20:00Z"
    }
  ]
}
```

---

## 📈 Progress Endpoints

### 1. Get Module Progress
```http
GET /courses/module-progress/?course_id=1
```

**Response (200 OK):**
```json
{
  "success": true,
  "data": [
    {
      "id": 1,
      "module_title": "Python Basics",
      "course_title": "Python for Beginners",
      "videos_completed": 5,
      "assignments_completed": 1,
      "quizzes_passed": 1,
      "is_unlocked": true,
      "is_completed": true,
      "completion_percentage": 100.0,
      "started_at": "2025-01-10T09:00:00Z",
      "completed_at": "2025-01-15T16:00:00Z"
    },
    {
      "id": 2,
      "module_title": "Advanced Python",
      "course_title": "Python for Beginners",
      "videos_completed": 2,
      "assignments_completed": 0,
      "quizzes_passed": 0,
      "is_unlocked": true,
      "is_completed": false,
      "completion_percentage": 33.3,
      "started_at": "2025-01-15T16:00:00Z",
      "completed_at": null
    }
  ]
}
```

---

## 🎓 Enrollment Endpoints

### 1. Enroll in Course
```http
POST /enrollments/
```

**Request Body:**
```json
{
  "course_id": 1,
  "enrollment_type": "individual"
}
```

**Response (201 Created):**
```json
{
  "success": true,
  "message": "Successfully enrolled in course",
  "data": {
    "id": 1,
    "course": {
      "id": 1,
      "title": "Python for Beginners",
      "price": 2999.00
    },
    "enrollment_type": "individual",
    "total_amount": 3538.82,
    "tax_amount": 539.82,
    "payment_status": "pending",
    "enrolled_on": "2025-01-15T11:00:00Z"
  }
}
```

### 2. Get User Enrollments
```http
GET /enrollments/my-courses/?status=active&page=1
```

**Query Parameters:**
- `status` (optional): active, completed, pending
- `page` (optional): Page number

**Response (200 OK):**
```json
{
  "success": true,
  "data": {
    "count": 3,
    "results": [
      {
        "id": 1,
        "course": {
          "id": 1,
          "title": "Python for Beginners",
          "thumbnail": "https://example.com/media/course_thumbnails/python.jpg"
        },
        "enrollment_type": "individual",
        "payment_status": "completed",
        "progress_percentage": 45.5,
        "completed_lessons": 20,
        "total_lessons": 44,
        "enrolled_on": "2025-01-15T11:00:00Z",
        "last_accessed": "2025-01-20T14:30:00Z"
      }
    ]
  }
}
```

### 3. Get Enrollment Details
```http
GET /enrollments/{enrollment_id}/
```

---

## 💳 Payment Endpoints

### 1. Create Payment Intent
```http
POST /payments/create-intent/
```

**Request Body:**
```json
{
  "enrollment_id": 1,
  "payment_method": "razorpay",
  "amount": 3538.82
}
```

**Response (200 OK):**
```json
{
  "success": true,
  "data": {
    "payment_intent_id": "pi_1234567890",
    "client_secret": "pi_1234567890_secret_abc123",
    "amount": 3538.82,
    "currency": "INR",
    "razorpay_order_id": "order_abc123def456"
  }
}
```

### 2. Confirm Payment
```http
POST /payments/confirm/
```

**Request Body:**
```json
{
  "payment_intent_id": "pi_1234567890",
  "payment_method_id": "pm_1234567890",
  "enrollment_id": 1
}
```

### 3. Get Payment History
```http
GET /payments/history/?page=1
```

**Response (200 OK):**
```json
{
  "success": true,
  "data": {
    "count": 5,
    "results": [
      {
        "id": 1,
        "enrollment": {
          "id": 1,
          "course_title": "Python for Beginners"
        },
        "amount": 3538.82,
        "tax_amount": 539.82,
        "payment_method": "razorpay",
        "status": "completed",
        "transaction_id": "txn_abc123def456",
        "payment_date": "2025-01-15T11:30:00Z",
        "invoice_number": "INV-2025-001"
      }
    ]
  }
}
```

---

## 📖 Learning Progress Endpoints

### 1. Update Lesson Progress
```http
POST /progress/lessons/{lesson_id}/
```

**Request Body:**
```json
{
  "completed_percentage": 85.0,
  "completed": false,
  "watch_time": 450
}
```

**Response (200 OK):**
```json
{
  "success": true,
  "data": {
    "lesson_id": 1,
    "completed_percentage": 85.0,
    "completed": false,
    "last_watched_at": "2025-01-20T15:45:00Z"
  }
}
```

### 2. Mark Lesson Complete
```http
POST /progress/lessons/{lesson_id}/complete/
```

### 3. Get Course Progress
```http
GET /progress/courses/{course_id}/
```

**Response (200 OK):**
```json
{
  "success": true,
  "data": {
    "course_id": 1,
    "overall_progress": 45.5,
    "completed_lessons": 20,
    "total_lessons": 44,
    "modules_progress": [
      {
        "module_id": 1,
        "module_title": "Introduction to Python",
        "progress_percentage": 100.0,
        "completed_lessons": 5,
        "total_lessons": 5
      },
      {
        "module_id": 2,
        "module_title": "Python Basics",
        "progress_percentage": 60.0,
        "completed_lessons": 6,
        "total_lessons": 10
      }
    ]
  }
}
```

---

## 👥 Team Endpoints (Optional)

### 1. Get User Teams
```http
GET /teams/my-teams/
```

### 2. Join Team
```http
POST /teams/{team_id}/join/
```

**Request Body:**
```json
{
  "join_code": "TEAM123ABC"
}
```

---

## 📱 Notifications Endpoints

### 1. Get Notifications
```http
GET /notifications/?page=1&unread_only=true
```

**Response (200 OK):**
```json
{
  "success": true,
  "data": {
    "count": 10,
    "unread_count": 3,
    "results": [
      {
        "id": 1,
        "title": "Course Progress Update",
        "message": "You've completed 50% of Python for Beginners",
        "type": "progress",
        "is_read": false,
        "created_at": "2025-01-20T10:00:00Z",
        "data": {
          "course_id": 1,
          "progress": 50.0
        }
      }
    ]
  }
}
```

### 2. Mark Notification as Read
```http
POST /notifications/{notification_id}/read/
```

### 3. Mark All Notifications as Read
```http
POST /notifications/mark-all-read/
```

---

## 🔍 Search Endpoints

### 1. Global Search
```http
GET /search/?q=python&type=courses&page=1
```

**Query Parameters:**
- `q`: Search query
- `type`: courses, lessons, instructors
- `page`: Page number

---

## 📊 Dashboard Endpoints

### 1. Student Dashboard
```http
GET /dashboard/student/
```

**Response (200 OK):**
```json
{
  "success": true,
  "data": {
    "enrolled_courses": 3,
    "completed_courses": 1,
    "in_progress_courses": 2,
    "total_watch_time": 7200,
    "recent_activity": [
      {
        "type": "lesson_completed",
        "course_title": "Python for Beginners",
        "lesson_title": "Variables in Python",
        "timestamp": "2025-01-20T14:30:00Z"
      }
    ],
    "recommended_courses": [
      {
        "id": 2,
        "title": "Advanced Python",
        "reason": "Based on your progress in Python for Beginners"
      }
    ]
  }
}
```

---

## 🎥 YouTube Integration Endpoints

### 1. Get Video Details
```http
GET /youtube/videos/{video_id}/
```

**Response (200 OK):**
```json
{
  "success": true,
  "data": {
    "video_id": "dQw4w9WgXcQ",
    "title": "Introduction to Python",
    "description": "Learn the basics of Python programming",
    "thumbnail_url": "https://img.youtube.com/vi/dQw4w9WgXcQ/maxresdefault.jpg",
    "duration": 600,
    "youtube_url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
    "channel": {
      "name": "CodeLearn Official",
      "id": "UC1234567890"
    }
  }
}
```

---

## 🔴 Error Responses

### Standard Error Format
```json
{
  "success": false,
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "The provided data is invalid",
    "details": {
      "email": ["This field is required"],
      "password": ["Password must be at least 8 characters"]
    }
  }
}
```

### Common Error Codes
- `VALIDATION_ERROR` (400): Invalid request data
- `AUTHENTICATION_REQUIRED` (401): User not authenticated
- `PERMISSION_DENIED` (403): User lacks required permissions
- `NOT_FOUND` (404): Resource not found
- `ALREADY_EXISTS` (409): Resource already exists
- `PAYMENT_REQUIRED` (402): Course requires payment
- `SERVER_ERROR` (500): Internal server error

---

## 📱 Flutter Implementation Examples

### 1. API Service Class
```dart
class ApiService {
  static const String baseUrl = 'https://your-domain.com/api/v1';
  
  static Future<Map<String, dynamic>> login(String email, String password) async {
    final response = await http.post(
      Uri.parse('$baseUrl/auth/login/'),
      headers: {'Content-Type': 'application/json'},
      body: jsonEncode({
        'email': email,
        'password': password,
      }),
    );
    
    return jsonDecode(response.body);
  }
  
  static Future<Map<String, dynamic>> getCourses({
    int page = 1,
    String? search,
    int? categoryId,
  }) async {
    String url = '$baseUrl/courses/?page=$page';
    if (search != null) url += '&search=$search';
    if (categoryId != null) url += '&category=$categoryId';
    
    final response = await http.get(
      Uri.parse(url),
      headers: await _getHeaders(),
    );
    
    return jsonDecode(response.body);
  }
  
  static Future<Map<String, String>> _getHeaders() async {
    final token = await SharedPreferences.getInstance()
        .then((prefs) => prefs.getString('auth_token'));
    
    return {
      'Content-Type': 'application/json',
      'Accept': 'application/json',
      if (token != null) 'Authorization': 'Bearer $token',
    };
  }
}
```

### 2. Model Classes
```dart
class Course {
  final int id;
  final String title;
  final String description;
  final double price;
  final double totalPrice;
  final String? thumbnail;
  final bool isEnrolled;
  
  Course({
    required this.id,
    required this.title,
    required this.description,
    required this.price,
    required this.totalPrice,
    this.thumbnail,
    this.isEnrolled = false,
  });
  
  factory Course.fromJson(Map<String, dynamic> json) {
    return Course(
      id: json['id'],
      title: json['title'],
      description: json['description'],
      price: double.parse(json['price'].toString()),
      totalPrice: double.parse(json['total_price'].toString()),
      thumbnail: json['thumbnail'],
      isEnrolled: json['is_enrolled'] ?? false,
    );
  }
}
```

---

## 🚀 Pagination

Most list endpoints support pagination:

**Request:**
```http
GET /courses/?page=2&page_size=20
```

**Response:**
```json
{
  "success": true,
  "data": {
    "count": 100,
    "next": "https://api.example.com/courses/?page=3",
    "previous": "https://api.example.com/courses/?page=1",
    "results": [...]
  }
}
```

---

## 🔐 Security Notes

1. **Always use HTTPS** in production
2. **Store tokens securely** using Flutter Secure Storage
3. **Implement token refresh** logic
4. **Validate SSL certificates**
5. **Handle expired tokens** gracefully
6. **Never log sensitive data**

---

## 📞 Support

For API support and questions:
- Email: api-support@codelearn.com
- Documentation: https://docs.codelearn.com/api
- Status Page: https://status.codelearn.com