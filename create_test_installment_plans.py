#!/usr/bin/env python
"""
Script to create test installment plan templates.
Run this from the Django shell: python manage.py shell < create_test_installment_plans.py
"""

import os
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'codelearn_lms.settings')
django.setup()

from apps.payments.models import InstallmentPlan
from apps.courses.models import Course, Category
from apps.users.models import User
from datetime import date, timedelta

def create_test_installment_plans():
    """Create realistic installment plan templates"""
    
    # Get or create an admin user for created_by field
    admin_user, created = User.objects.get_or_create(
        email='admin@codelearn.com',
        defaults={
            'name': 'Admin User',
            'username': 'admin',
            'is_staff': True,
            'is_active': True,
            'role': 'admin'
        }
    )
    
    if created:
        admin_user.set_password('admin123')
        admin_user.save()
        print(f"✅ Created admin user: {admin_user.email}")
    else:
        print(f"✅ Using existing admin user: {admin_user.email}")

    # Get a sample course (or use first available course)
    try:
        sample_course = Course.objects.first()
        course_price = sample_course.total_price if sample_course else 25000
        print(f"✅ Using sample course price: ₹{course_price}")
    except:
        course_price = 25000
        print(f"✅ Using default course price: ₹{course_price}")

    # Test Plan Templates to Create
    test_plans = [
        {
            'name': 'Quick 2-Month Plan',
            'description': 'Fast payment plan with higher monthly amounts. Perfect for professionals who want to complete payment quickly.',
            'total_installments': 2,
            'frequency': 'monthly',
            'installment_amount': course_price / 2,
            'start_date': date.today() + timedelta(days=7),
            'color_code': '#28a745'  # Green
        },
        {
            'name': 'Standard 3-Month Plan',
            'description': 'Most popular plan with balanced monthly payments. Ideal for working professionals.',
            'total_installments': 3,
            'frequency': 'monthly', 
            'installment_amount': course_price / 3,
            'start_date': date.today() + timedelta(days=7),
            'color_code': '#007bff'  # Blue
        },
        {
            'name': 'Flexible 4-Month Plan',
            'description': 'Moderate monthly payments with extra flexibility. Good for students with part-time income.',
            'total_installments': 4,
            'frequency': 'monthly',
            'installment_amount': course_price / 4,
            'start_date': date.today() + timedelta(days=14),
            'color_code': '#17a2b8'  # Teal
        },
        {
            'name': 'Budget 6-Month Plan',
            'description': 'Lowest monthly payments for budget-conscious learners. Perfect for students.',
            'total_installments': 6,
            'frequency': 'monthly',
            'installment_amount': course_price / 6,
            'start_date': date.today() + timedelta(days=14),
            'color_code': '#ffc107'  # Yellow
        },
        {
            'name': 'Extended 12-Month Plan',
            'description': 'Ultra-low monthly payments spread over a full year. Maximum affordability.',
            'total_installments': 12,
            'frequency': 'monthly',
            'installment_amount': course_price / 12,
            'start_date': date.today() + timedelta(days=30),
            'color_code': '#6c757d'  # Gray
        },
        {
            'name': 'Weekly 8-Week Plan',
            'description': 'Weekly payments for faster completion. Good for those with weekly income.',
            'total_installments': 8,
            'frequency': 'custom',  # Weekly equivalent
            'installment_amount': course_price / 8,
            'start_date': date.today() + timedelta(days=7),
            'color_code': '#e83e8c'  # Pink
        },
        {
            'name': 'Corporate 3-Month Plan',
            'description': 'Business-friendly payment plan with quarterly structure for corporate enrollments.',
            'total_installments': 3,
            'frequency': 'monthly',
            'installment_amount': course_price / 3,
            'start_date': date.today() + timedelta(days=30),
            'color_code': '#6610f2'  # Purple
        },
        {
            'name': 'Student Special 5-Month Plan',
            'description': 'Specially designed for students with limited income. Includes grace period.',
            'total_installments': 5,
            'frequency': 'monthly',
            'installment_amount': course_price / 5,
            'start_date': date.today() + timedelta(days=21),
            'color_code': '#fd7e14'  # Orange
        }
    ]

    created_plans = []
    
    for plan_data in test_plans:
        try:
            # Check if plan already exists
            existing_plan = InstallmentPlan.objects.filter(
                total_installments=plan_data['total_installments'],
                installment_amount=plan_data['installment_amount']
            ).first()
            
            if existing_plan:
                print(f"⚠️  Similar plan already exists: {existing_plan}")
                continue
            
            # Create the installment plan
            plan = InstallmentPlan.objects.create(
                total_installments=plan_data['total_installments'],
                installment_amount=plan_data['installment_amount'],
                frequency=plan_data['frequency'],
                start_date=plan_data['start_date']
            )
            
            created_plans.append({
                'plan': plan,
                'name': plan_data['name'],
                'description': plan_data['description'],
                'color_code': plan_data['color_code']
            })
            
            print(f"✅ Created: {plan_data['name']}")
            print(f"   💰 {plan_data['total_installments']} × ₹{plan_data['installment_amount']:.2f}")
            print(f"   📅 Starting: {plan_data['start_date']}")
            print(f"   📝 {plan_data['description']}")
            print()
            
        except Exception as e:
            print(f"❌ Error creating {plan_data['name']}: {str(e)}")
    
    print(f"\n🎉 Successfully created {len(created_plans)} installment plans!")
    
    # Display summary
    print("\n" + "="*80)
    print("📊 INSTALLMENT PLANS SUMMARY")
    print("="*80)
    
    all_plans = InstallmentPlan.objects.all().order_by('installment_amount')
    
    for i, plan in enumerate(all_plans, 1):
        total_amount = plan.installment_amount * plan.total_installments
        print(f"{i:2d}. {plan.total_installments:2d} installments × ₹{plan.installment_amount:8.2f} = ₹{total_amount:8.2f} | {plan.frequency.title():8s} | Due: {plan.start_date}")
    
    print("\n💡 These plans can now be assigned to enrollments!")
    print("💡 You can modify any plan amounts or create additional plans as needed.")
    
    return created_plans

def create_sample_enrollment_with_plan():
    """Create a sample enrollment using one of the installment plans"""
    try:
        from apps.payments.models import Enrollment
        
        # Get sample data
        user = User.objects.filter(role='student').first()
        course = Course.objects.first()
        plan = InstallmentPlan.objects.filter(total_installments=3).first()
        
        if not all([user, course, plan]):
            print("❌ Missing required data for sample enrollment")
            return None
        
        # Create sample enrollment
        enrollment = Enrollment.objects.create(
            user=user,
            course=course,
            enrollment_type='individual',
            total_amount=course.total_price,
            tax_amount=course.tax_amount,
            payment_status='pending',
            has_installment_plan=True
        )
        
        # Link the installment plan (you'll need to create this relationship)
        print(f"✅ Created sample enrollment: {enrollment}")
        print(f"   Student: {user.name}")
        print(f"   Course: {course.title}")
        print(f"   Plan: {plan.total_installments} installments of ₹{plan.installment_amount}")
        
        return enrollment
        
    except Exception as e:
        print(f"❌ Error creating sample enrollment: {str(e)}")
        return None

if __name__ == "__main__":
    print("🚀 Creating Test Installment Plans...")
    print("=" * 80)
    
    created_plans = create_test_installment_plans()
    
    print("\n" + "="*80)
    print("🎯 NEXT STEPS:")
    print("="*80)
    print("1. Go to Custom Admin → Installment Plans to see all plans")
    print("2. Create enrollments and assign these plans")
    print("3. Test the payment workflow")
    print("4. Modify plan amounts as needed")
    print("\n🎉 Setup complete! Ready for testing.")