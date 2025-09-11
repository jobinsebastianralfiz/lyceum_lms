#!/usr/bin/env python3
"""
Debug script to check enrollment status discrepancies
Run this to identify the exact issue with enrollment checks
"""

import os
import sys
import django

# Setup Django environment
sys.path.append('/Users/jobinsebastian/djangoprojects/lms')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'codelearn_lms.settings')
django.setup()

from apps.payments.models import Enrollment
from apps.courses.models import Course
from apps.users.models import User

def debug_enrollment_issues():
    print("=== ENROLLMENT DEBUG REPORT ===\n")
    
    # Get all enrollments
    enrollments = Enrollment.objects.all()
    print(f"Total enrollments: {enrollments.count()}\n")
    
    # Check payment status distribution
    print("Payment Status Distribution:")
    for status, display in Enrollment.PAYMENT_STATUS_CHOICES:
        count = enrollments.filter(payment_status=status).count()
        print(f"  {display} ({status}): {count}")
    
    print(f"\nActive vs Inactive:")
    print(f"  Active: {enrollments.filter(active=True).count()}")
    print(f"  Inactive: {enrollments.filter(active=False).count()}")
    
    # Check for problematic enrollments
    print(f"\n=== POTENTIAL ISSUES ===")
    
    # Enrollments that are active but not completed payment
    problematic = enrollments.filter(active=True).exclude(payment_status='completed')
    print(f"Active enrollments with non-completed payment: {problematic.count()}")
    
    if problematic.exists():
        print("Details:")
        for enrollment in problematic[:5]:  # Show first 5
            print(f"  User: {enrollment.user.email}")
            print(f"  Course: {enrollment.course.title}")
            print(f"  Payment Status: {enrollment.payment_status}")
            print(f"  Total Amount: ${enrollment.total_amount}")
            print(f"  Paid Amount: ${enrollment.paid_amount}")
            print("  ---")
    
    # Check for enrollments with payment_status='completed' but active=False
    inactive_completed = enrollments.filter(payment_status='completed', active=False)
    print(f"\nCompleted payments but inactive enrollments: {inactive_completed.count()}")
    
    if inactive_completed.exists():
        print("Details:")
        for enrollment in inactive_completed[:5]:
            print(f"  User: {enrollment.user.email}")
            print(f"  Course: {enrollment.course.title}")
            print("  ---")

if __name__ == "__main__":
    debug_enrollment_issues()