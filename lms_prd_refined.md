# 📘 Product Requirements Document (PRD) - Learning Management System

## Project Title: CodeLearn LMS - Fee-Based Learning Management System

---

## 1. 🧭 Executive Summary

CodeLearn LMS is a comprehensive online learning platform where students can access recorded courses through direct purchase or admin-assigned enrollments. The system features robust fee management with installment support, tax calculation (18% GST), and detailed billing. Admins have complete control over course creation, student management, and fee collection, while students can track their learning progress and fee status.

---

## 2. 🎯 Goals & Objectives

- **Course Delivery**: Provide recorded video-based courses to students online
- **Flexible Enrollment**: Support both student self-registration/purchase and admin-assigned enrollments
- **Fee Management**: Handle course fees with installment options and comprehensive tracking
- **Tax Compliance**: Calculate and display 18% GST on all transactions with proper tax invoicing
- **Administrative Control**: Enable admins to manage courses, categories, students, and fee collection
- **Student Experience**: Provide intuitive dashboards for course access and fee tracking

---

## 3. 👥 User Roles & Permissions

| Role | Access & Actions |
|------|------------------|
| **Student** | Register/Login, Browse courses, Purchase courses, View enrolled courses, Watch videos, Track fee status, View tax bills, Make fee payments |
| **Admin** | Manage users, Create/manage courses and categories, Add students manually, Assign courses, Accept fee payments, Generate tax invoices, View analytics |

---

## 4. 📌 Key Features & Modules

### A. Authentication & User Management
- Student registration and login (email/password)
- Admin login via separate portal
- Password reset functionality
- User profile management

### B. Course & Category Management
- **Course Creation**:
  - Title, description, category assignment
  - Price configuration (free or paid)
  - Course structure: Modules → Chapters → Video lessons
  - **YouTube Integration**:
    - Connect to admin's YouTube channel via API
    - Fetch video lists from channel/playlists
    - Auto-populate video metadata (title, description, thumbnail, duration)
    - Select videos for course inclusion
    - Support for unlisted videos for premium content
  - Course publish/unpublish status
- **Category Management**:
  - Create course categories
  - Organize courses by subject/topic
  - Category-based course filtering

### C. Student Dashboard
- List of enrolled/purchased courses
- Course progress tracking
- **Video Learning Experience**:
  - Integrated YouTube player with custom controls
  - Progress tracking and resume functionality
  - Video quality selection
  - Playback speed control
  - Access restricted based on enrollment status
- Access to downloadable resources
- **Fee Management Section**:
  - Current fee status and balance
  - Payment history
  - Installment schedule
  - Tax bill downloads
  - Payment gateway integration

### D. Fee Management System
- **Payment Options**:
  - Full payment at enrollment
  - Monthly installment plans
  - Custom installment schedules
- **Fee Tracking**:
  - Outstanding balance calculation
  - Payment due dates
  - Late payment notifications
- **Tax Calculation**:
  - Automatic 18% GST calculation
  - Tax-inclusive pricing display
  - Separate tax amount breakdown

### E. Admin Panel
- **Student Management**:
  - Add students manually
  - Assign courses directly
  - View student progress and fee status
  - Bulk student operations
- **Course Management**:
  - Create and edit courses
  - **YouTube Video Management**:
    - Connect YouTube channel via OAuth
    - Browse and select videos from channel
    - Fetch video metadata automatically
    - Organize videos into course modules
    - Set video access permissions
    - Preview videos before adding to courses
  - Manage course categories
  - Course analytics and enrollment stats
- **Fee Management**:
  - Accept fee payments (cash/online)
  - Generate installment schedules
  - Fee collection tracking
  - Outstanding payment reports
- **Tax & Billing**:
  - Generate tax invoices
  - Tax collection reports
  - GST compliance reporting

### F. Payment & Billing System
- **Payment Gateway Integration**:
  - Razorpay for Indian payments
  - Support for UPI, cards, net banking
- **Invoice Generation**:
  - Automated tax invoice creation
  - PDF invoice downloads
  - Invoice numbering system
- **Payment Tracking**:
  - Real-time payment status updates
  - Payment confirmation emails
  - Receipt generation

---

## 5. 🧱 Database Model

### Users
```python
- id
- name
- email
- password (hashed)
- role [student, admin]
- phone_number
- address
- created_at
- updated_at
```

### Course
```python
- id
- title
- description
- category_id
- price (excluding tax)
- tax_rate (default: 18%)
- thumbnail
- preview_video
- is_published
- created_by
- created_at
- updated_at
```

### Category
```python
- id
- name
- description
- created_at
- updated_at
```

### Module
```python
- id
- course_id
- title
- order
- created_at
- updated_at
```

### VideoLesson
```python
- id
- module_id
- title
- youtube_video_id
- youtube_url
- thumbnail_url
- duration
- description
- resource_file
- order
- is_preview (free preview for non-enrolled students)
- created_at
- updated_at
```

### YouTubeChannelConfig
```python
- id
- admin_user_id
- channel_id
- channel_name
- access_token
- refresh_token
- last_sync_at
- created_at
- updated_at
```

### Enrollment
```python
- id
- user_id
- course_id
- enrollment_type [purchased, admin_assigned]
- enrolled_on
- total_amount (including tax)
- tax_amount
- payment_status [pending, partial, completed]
- installment_plan_id
- active
- created_at
- updated_at
```

### InstallmentPlan
```python
- id
- enrollment_id
- total_installments
- installment_amount
- frequency [monthly, custom]
- start_date
- created_at
- updated_at
```

### Payment
```python
- id
- enrollment_id
- installment_number
- amount
- tax_amount
- payment_method
- transaction_id
- payment_date
- due_date
- status [pending, completed, overdue]
- invoice_number
- created_at
- updated_at
```

### TaxInvoice
```python
- id
- enrollment_id
- payment_id
- invoice_number
- invoice_date
- subtotal
- tax_rate
- tax_amount
- total_amount
- invoice_pdf_path
- created_at
- updated_at
```

### StudentProgress
```python
- id
- user_id
- course_id
- video_lesson_id
- completed_percentage
- last_watched_at
- completed
- created_at
- updated_at
```

---

## 6. 📱 Frontend Pages

### Student Portal
- **Authentication**:
  - Login/Register page
  - Password reset
- **Dashboard**:
  - Course overview
  - Progress tracking
  - Recent activity
- **Course Pages**:
  - Course catalog with category filters
  - Course detail page with pricing
  - **YouTube Video Player**:
    - Custom embedded YouTube player
    - Access control based on enrollment
    - Progress tracking and bookmarking
    - Video quality and speed controls
    - Prevention of unauthorized access
  - Course materials download
- **Fee Management**:
  - Fee dashboard
  - Payment history
  - Installment schedule
  - Tax invoice downloads
  - Payment gateway integration

### Admin Portal
- **Authentication**:
  - Admin login
  - Dashboard overview
- **Student Management**:
  - Student list and search
  - Add/edit students
  - Assign courses
  - View student progress
- **Course Management**:
  - Course list and creation
  - **YouTube Integration Panel**:
    - YouTube channel connection setup
    - Video import from channel/playlists
    - Bulk video metadata import
    - Video access permission settings
    - Sync with YouTube for updates
  - Category management
  - Content organization tools
- **Fee Management**:
  - Payment collection interface
  - Outstanding fee reports
  - Installment plan creation
  - Tax invoice generation
- **Analytics**:
  - Enrollment statistics
  - Revenue reports
  - Course performance metrics

---

## 7. 🔧 Technology Stack

| Layer | Technology |
|-------|------------|
| **Frontend** | React.js with Material-UI/Tailwind CSS |
| **Backend** | Django + Django REST Framework |
| **Database** | PostgreSQL |
| **Authentication** | JWT + Django Auth |
| **Video Integration** | YouTube Data API v3 + YouTube Player API |
| **Payment Gateway** | Razorpay (Primary), Stripe (Optional) |
| **File Storage** | AWS S3 / Local Storage (for resources) |
| **PDF Generation** | ReportLab (Python) |
| **Email Service** | SendGrid / AWS SES |
| **Deployment** | Docker + Nginx + Gunicorn on AWS/DigitalOcean |

---

## 8. 📈 Milestones & Timeline

| Milestone | Time Estimate |
|-----------|---------------|
| **UI/UX Design** | 1 week |
| **Authentication & User Management** | 1 week |
| **YouTube API Integration** | 1 week |
| **Course & Category Management** | 1.5 weeks |
| **Video Delivery & Student Dashboard** | 1.5 weeks |
| **Fee Management System** | 2 weeks |
| **Payment Gateway Integration** | 1 week |
| **Tax Invoice Generation** | 1 week |
| **Admin Panel** | 1.5 weeks |
| **Testing & Bug Fixes** | 1 week |
| **Deployment & Setup** | 3 days |

**Total Estimated Time: ~11-12 weeks**

---

## 9. 🎬 YouTube API Integration Details

### YouTube Data API v3 Features
- **Channel Connection**: OAuth 2.0 authentication with YouTube
- **Video Fetching**: Retrieve video metadata from your channel
- **Playlist Support**: Import videos from specific playlists
- **Metadata Extraction**: Auto-populate title, description, thumbnail, duration
- **Real-time Sync**: Periodic synchronization with YouTube for updates

### YouTube Player API Features
- **Embedded Player**: Custom-styled YouTube player integration
- **Access Control**: Show/hide videos based on enrollment status
- **Progress Tracking**: Monitor video watch time and completion
- **Player Controls**: Custom controls for educational experience
- **Quality Selection**: Allow students to choose video quality

### Implementation Considerations
- **API Quotas**: Manage YouTube API daily quotas efficiently
- **Caching Strategy**: Cache video metadata to reduce API calls
- **Error Handling**: Graceful handling of deleted/private videos
- **Content Security**: Prevent unauthorized video access
- **Mobile Compatibility**: Ensure player works across devices

### Video Access Control
- **Enrollment-based Access**: Only enrolled students can watch full videos
- **Preview Mode**: Free preview clips for non-enrolled users
- **Time-based Access**: Optional time-limited access for courses
- **Download Prevention**: Disable video downloads through platform controls

---

## 10. 🔐 Security & Compliance

### Data Security
- Password hashing with bcrypt
- JWT token-based authentication
- HTTPS enforcement
- Input validation and sanitization
- SQL injection prevention

### Tax Compliance
- GST calculation as per Indian tax laws
- Proper invoice numbering sequence
- Tax invoice format compliance
- Digital signature on invoices
- Audit trail for all transactions

### YouTube API Security
- OAuth 2.0 secure authentication
- API key management and rotation
- Rate limiting and quota management
- Secure token storage and refresh

### Payment Security
- PCI DSS compliant payment processing
- Secure payment gateway integration
- Transaction encryption
- Payment failure handling

---

## 11. 📄 Optional Add-ons (Future Enhancements)

- **Advanced Analytics**: Detailed course performance and student engagement metrics
- **Mobile App**: iOS/Android app using React Native/Flutter
- **Bulk Operations**: CSV import/export for students and courses
- **Notification System**: Email/SMS notifications for due payments and course updates
- **Multi-language Support**: Hindi and regional language support
- **Advanced Reporting**: Custom report generation for admin
- **Integration APIs**: Third-party system integration capabilities
- **Automated Reminders**: Payment due date reminders and course completion notifications

---

## 11. 🎯 Success Metrics

- **Student Engagement**: Course completion rates, video watch time
- **Financial Metrics**: Revenue tracking, payment collection efficiency
- **System Performance**: Page load times, video streaming quality
- **User Satisfaction**: Student feedback scores, support ticket resolution time
- **Administrative Efficiency**: Time saved in student and course management

---

*This PRD serves as the foundation for building a comprehensive, tax-compliant Learning Management System focused on effective fee management and course delivery.*