#!/usr/bin/env python3
"""
Test script to debug enrollment issues
Run with: python manage.py shell < test_enrollment.py
"""

from django.contrib.auth import get_user_model
from apps.courses.models import Course
from apps.payments.models import Enrollment
from django.conf import settings

User = get_user_model()

print("🔍 ENROLLMENT DEBUG INFORMATION")
print("=" * 50)

# Check if any users exist
users_count = User.objects.count()
print(f"📊 Total users: {users_count}")

if users_count > 0:
    # Get first user for testing
    test_user = User.objects.first()
    print(f"🧑 Test user: {test_user.email} (ID: {test_user.id})")
    print(f"   - Is authenticated: {test_user.is_authenticated}")
    print(f"   - Is active: {test_user.is_active}")
else:
    print("❌ No users found! Create a user account first.")

print()

# Check courses
courses_count = Course.objects.count()
print(f"📚 Total courses: {courses_count}")

published_courses = Course.objects.filter(is_published=True, allow_public_enrollment=True)
print(f"📖 Published courses with public enrollment: {published_courses.count()}")

if published_courses.exists():
    for course in published_courses[:3]:  # Show first 3 courses
        print(f"   📘 {course.title}")
        print(f"      - ID: {course.id}")
        print(f"      - Is free: {course.is_free_course}")
        print(f"      - Price: {course.price}")
        print(f"      - Total price: {course.total_price}")
        print(f"      - Tax amount: {course.tax_amount}")
        
        if users_count > 0:
            # Check if test user is enrolled
            is_enrolled = Enrollment.objects.filter(
                user=test_user, 
                course=course, 
                active=True
            ).exists()
            print(f"      - Test user enrolled: {is_enrolled}")
        print()
else:
    print("❌ No published courses with public enrollment found!")
    print("   Create a course and set is_published=True, allow_public_enrollment=True")

print()

# Check Razorpay settings
print("💳 RAZORPAY SETTINGS")
print("-" * 30)
razorpay_key = getattr(settings, 'RAZORPAY_KEY_ID', None)
razorpay_secret = getattr(settings, 'RAZORPAY_KEY_SECRET', None)

print(f"🔑 Razorpay Key ID: {'✅ Set' if razorpay_key else '❌ Missing'}")
print(f"🔐 Razorpay Secret: {'✅ Set' if razorpay_secret else '❌ Missing'}")

if razorpay_key:
    print(f"   Key preview: {razorpay_key[:8]}...")

print()

# Check enrollments
enrollments_count = Enrollment.objects.count()
print(f"🎓 Total enrollments: {enrollments_count}")

if enrollments_count > 0:
    recent_enrollments = Enrollment.objects.order_by('-created_at')[:5]
    print("📋 Recent enrollments:")
    for enrollment in recent_enrollments:
        print(f"   - {enrollment.user.email} → {enrollment.course.title}")
        print(f"     Status: {enrollment.payment_status} | Amount: ₹{enrollment.total_amount}")

print()
print("🚀 TROUBLESHOOTING TIPS:")
print("=" * 50)
print("1. Ensure user is logged in before clicking 'Enroll Now'")
print("2. Check browser console for JavaScript errors")
print("3. Verify course has is_published=True and allow_public_enrollment=True")
print("4. For paid courses, ensure Razorpay keys are configured")
print("5. Check Django server logs for debug output")