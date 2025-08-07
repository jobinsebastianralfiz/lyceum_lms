# Student Course Purchase API Documentation

## 🎯 Overview
This API enables students to purchase courses directly from the mobile app, which automatically creates enrollment and payment records in the backend system.

## 🔑 Authentication
All endpoints require JWT token authentication:
```http
Authorization: Bearer {access_token}
```

---

## 📋 API Endpoints

### 1. Get Course Pricing Breakdown
**Get pricing details before purchase**

```http
GET /api/payments/course/{course_id}/pricing/
```

**Response (200 OK):**
```json
{
  "course_pricing": {
    "id": 1,
    "title": "Python Mastery Course",
    "base_price": "2999.00",
    "tax_rate": 18.0,
    "tax_amount": "539.82", 
    "total_amount": "3538.82",
    "is_free": false
  },
  "is_enrolled": false,
  "can_purchase": true
}
```

### 2. Purchase Course (Auto-Enrollment)
**Main endpoint for course purchase with automatic enrollment**

```http
POST /api/payments/purchase-course/
```

**Request Body:**
```json
{
  "course_id": 1,
  "payment_method": "razorpay",
  "transaction_id": "pay_xxxxxxxxxxxxxxxx",
  "payment_gateway_response": {
    "razorpay_payment_id": "pay_xxxxxxxxxxxxxxxx",
    "razorpay_order_id": "order_xxxxxxxxxxxxxxxx",
    "razorpay_signature": "signature_hash",
    "amount": 353882,
    "currency": "INR",
    "status": "captured"
  }
}
```

**Response (201 Created):**
```json
{
  "message": "Course purchased and enrollment created successfully",
  "enrollment_id": 15,
  "payment_id": 23,
  "total_amount": 3538.82,
  "payment_status": "completed",
  "course_title": "Python Mastery Course"
}
```

**Error Responses:**
```json
// Already enrolled
{
  "error": "You are already enrolled in this course"
}

// Course not found
{
  "error": "Course not found"
}

// Invalid data
{
  "error": {
    "course_id": ["This field is required."],
    "payment_method": ["This field is required."]
  }
}
```

### 3. Get My Enrollments
**List all courses the student is enrolled in**

```http
GET /api/payments/my-enrollments/
```

**Response (200 OK):**
```json
[
  {
    "id": 15,
    "user": 5,
    "user_name": "John Doe",
    "course": 1,
    "course_title": "Python Mastery Course",
    "course_price": "2999.00",
    "team": null,
    "enrollment_type": "individual",
    "enrolled_on": "2025-01-15T10:30:00Z",
    "total_amount": "3538.82",
    "tax_amount": "539.82", 
    "payment_status": "completed",
    "has_installment_plan": false,
    "active": true,
    "paid_amount": "2999.00",
    "outstanding_amount": "0.00",
    "payments": [
      {
        "id": 23,
        "installment_number": 1,
        "amount": "2999.00",
        "tax_amount": "539.82",
        "payment_method": "razorpay",
        "transaction_id": "pay_xxxxxxxxxxxxxxxx",
        "payment_date": "2025-01-15T10:30:00Z",
        "due_date": "2025-01-15",
        "status": "completed",
        "invoice_number": null,
        "notes": "Auto-generated from app purchase. Gateway Response: {...}"
      }
    ]
  }
]
```

### 4. Get Payment History for Enrollment
**Get detailed payment history for a specific enrollment**

```http
GET /api/payments/enrollments/{enrollment_id}/payments/
```

**Response (200 OK):**
```json
{
  "enrollment": {
    "id": 15,
    "course_title": "Python Mastery Course",
    "total_amount": "3538.82",
    "payment_status": "completed",
    "outstanding_amount": "0.00"
  },
  "payments": [
    {
      "id": 23,
      "enrollment": 15,
      "enrollment_course": "Python Mastery Course",
      "enrollment_user": "John Doe",
      "installment_number": 1,
      "amount": "2999.00",
      "tax_amount": "539.82",
      "payment_method": "razorpay",
      "transaction_id": "pay_xxxxxxxxxxxxxxxx",
      "payment_date": "2025-01-15T10:30:00Z",
      "due_date": "2025-01-15",
      "status": "completed",
      "invoice_number": null,
      "notes": "Auto-generated from app purchase. Gateway Response: {...}",
      "created_at": "2025-01-15T10:30:00Z",
      "updated_at": "2025-01-15T10:30:00Z"
    }
  ]
}
```

---

## 💳 Payment Methods Supported

| Value | Description |
|-------|-------------|
| `razorpay` | Razorpay Gateway |
| `stripe` | Stripe Gateway |
| `paytm` | Paytm Gateway |
| `phonepe` | PhonePe Gateway |
| `gpay` | Google Pay |
| `other` | Other Payment Method |

---

## 🔄 App Integration Flow

### Step 1: Course Discovery
```dart
// Get course list
GET /api/courses/

// Get course details  
GET /api/courses/{course_id}/
```

### Step 2: Pricing Preview
```dart
// Show pricing breakdown before payment
GET /api/payments/course/{course_id}/pricing/

// Example response shows:
// - Base price: ₹2,999
// - Tax (18%): ₹539.82  
// - Total: ₹3,538.82
```

### Step 3: Payment Processing
```dart
// 1. Student initiates payment in app
// 2. App integrates with Razorpay/Stripe
// 3. On successful payment, call backend:

POST /api/payments/purchase-course/
{
  "course_id": 1,
  "payment_method": "razorpay", 
  "transaction_id": "pay_xxxxx",
  "payment_gateway_response": {
    // Complete gateway response
  }
}
```

### Step 4: Auto-Enrollment
```dart
// Backend automatically:
// ✅ Creates Enrollment record
// ✅ Creates Payment record  
// ✅ Creates Tax Invoice
// ✅ Marks enrollment as completed
// ✅ Student gets immediate course access
```

### Step 5: Course Access
```dart
// Student can now access course content:
GET /api/courses/enrolled/  // Shows enrolled courses
GET /api/courses/{course_id}/  // Access course modules
```

---

## 🛡️ Security Features

1. **JWT Authentication** - All endpoints protected
2. **Duplicate Prevention** - Prevents multiple enrollments
3. **Data Validation** - Validates course_id and payment data
4. **Transaction Integrity** - Atomic database operations
5. **Payment Verification** - Stores complete gateway response

---

## 📱 Flutter Integration Example

```dart
class CourseService {
  
  // Get course pricing
  Future<CoursePricing> getCoursePricing(int courseId) async {
    final response = await http.get(
      Uri.parse('$baseUrl/payments/course/$courseId/pricing/'),
      headers: {'Authorization': 'Bearer $token'}
    );
    return CoursePricing.fromJson(json.decode(response.body));
  }
  
  // Purchase course after payment success
  Future<PurchaseResult> purchaseCourse({
    required int courseId,
    required String paymentMethod,
    required String transactionId,
    required Map<String, dynamic> gatewayResponse
  }) async {
    
    final response = await http.post(
      Uri.parse('$baseUrl/payments/purchase-course/'),
      headers: {
        'Authorization': 'Bearer $token',
        'Content-Type': 'application/json'
      },
      body: json.encode({
        'course_id': courseId,
        'payment_method': paymentMethod,
        'transaction_id': transactionId,
        'payment_gateway_response': gatewayResponse
      })
    );
    
    if (response.statusCode == 201) {
      return PurchaseResult.fromJson(json.decode(response.body));
    } else {
      throw Exception('Purchase failed');
    }
  }
}
```

---

## 🎯 Benefits

✅ **Admin-Centric System Maintained** - Admin can still manually manage everything  
✅ **Student Self-Service** - Students can purchase courses independently  
✅ **Automatic Processing** - No manual intervention needed  
✅ **Single Payment Flow** - One payment, instant enrollment  
✅ **Tax Compliance** - Automatic GST calculation and invoicing  
✅ **Payment Gateway Flexibility** - Supports multiple payment methods  
✅ **Complete Audit Trail** - All payment details stored  

The system now supports both admin-managed enrollments AND student self-enrollment! 🚀