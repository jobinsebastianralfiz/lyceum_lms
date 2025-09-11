#!/usr/bin/env python3
"""
Test the new EnrollmentService to verify it works correctly
"""

import os
import sys
import django

# Setup Django environment
sys.path.append('/Users/jobinsebastian/djangoprojects/lms')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'codelearn_lms.settings')
django.setup()

from apps.payments.services import EnrollmentService
from apps.payments.models import Enrollment
from apps.users.models import User
from apps.courses.models import Course

def test_enrollment_service():
    print("=== TESTING ENROLLMENT SERVICE ===\n")
    
    # Get test data
    enrollments = Enrollment.objects.all()
    print(f"Total enrollments: {enrollments.count()}")
    
    for enrollment in enrollments:
        user = enrollment.user
        course = enrollment.course
        
        print(f"\n--- Testing: {user.email} → {course.title} ---")
        print(f"Payment Status: {enrollment.payment_status}")
        print(f"Active: {enrollment.active}")
        
        # Test old logic (would fail)
        old_logic = Enrollment.objects.filter(
            user=user, 
            course=course,
            payment_status='completed'
        ).exists()
        print(f"Old Logic (completed only): {old_logic}")
        
        # Test new service methods
        can_rate = EnrollmentService.can_rate_course(user, course)
        is_enrolled = EnrollmentService.is_user_enrolled(user, course)
        has_partial = EnrollmentService.has_partial_payment(user, course)
        
        print(f"New Service - Can Rate: {can_rate}")
        print(f"New Service - Is Enrolled: {is_enrolled}")
        print(f"New Service - Has Partial Payment: {has_partial}")

if __name__ == "__main__":
    test_enrollment_service()