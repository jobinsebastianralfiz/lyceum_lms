#!/usr/bin/env python
import os
import django
from decimal import Decimal
from datetime import date, timedelta

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'codelearn_lms.settings')
django.setup()

from apps.users.models import User
from apps.courses.models import Category, Course, Module, VideoLesson
from apps.payments.models import Enrollment, Payment
from apps.notifications.models import EmailTemplate

def create_sample_data():
    print("Creating sample data...")
    
    # Create admin user if not exists
    admin_user, created = User.objects.get_or_create(
        email='admin@codelearn.com',
        defaults={
            'username': 'admin@codelearn.com',
            'name': 'Admin User',
            'role': 'admin',
            'is_staff': True,
            'is_superuser': True,
        }
    )
    if created:
        admin_user.set_password('admin123')
        admin_user.save()
        print(f"Created admin user: {admin_user.email}")
    
    # Create sample students
    students = []
    for i in range(5):
        student, created = User.objects.get_or_create(
            email=f'student{i+1}@example.com',
            defaults={
                'username': f'student{i+1}@example.com',
                'name': f'Student {i+1}',
                'role': 'student',
                'phone_number': f'+91987654321{i}',
                'address': f'Address {i+1}, City, State'
            }
        )
        if created:
            student.set_password('student123')
            student.save()
            students.append(student)
            print(f"Created student: {student.email}")
    
    # Create categories
    categories_data = [
        ('Web Development', 'Learn modern web development technologies'),
        ('Data Science', 'Master data science and machine learning'),
        ('Mobile Development', 'Build mobile apps for iOS and Android'),
        ('DevOps', 'Learn deployment and infrastructure management'),
    ]
    
    categories = []
    for name, desc in categories_data:
        category, created = Category.objects.get_or_create(
            name=name,
            defaults={'description': desc}
        )
        categories.append(category)
        if created:
            print(f"Created category: {category.name}")
    
    # Create courses
    courses_data = [
        ('Complete Python Web Development', categories[0], Decimal('4999.00'), 'Learn Python Django framework from scratch'),
        ('React.js Masterclass', categories[0], Decimal('3999.00'), 'Build modern web applications with React'),
        ('Data Science with Python', categories[1], Decimal('5999.00'), 'Complete data science course with Python'),
        ('Machine Learning Fundamentals', categories[1], Decimal('6999.00'), 'Learn ML algorithms and implementations'),
        ('Flutter Mobile Development', categories[2], Decimal('4499.00'), 'Build cross-platform mobile apps'),
    ]
    
    courses = []
    for title, category, price, description in courses_data:
        course, created = Course.objects.get_or_create(
            title=title,
            defaults={
                'description': description,
                'category': category,
                'price': price,
                'tax_rate': Decimal('18.0'),
                'is_published': True,
                'created_by': admin_user,
            }
        )
        courses.append(course)
        if created:
            print(f"Created course: {course.title}")
            
            # Create modules for each course
            modules_data = [
                f'Introduction to {title}',
                f'Basic Concepts',
                f'Intermediate Topics',
                f'Advanced Concepts',
                f'Project Work'
            ]
            
            for i, module_title in enumerate(modules_data):
                module, module_created = Module.objects.get_or_create(
                    course=course,
                    title=module_title,
                    defaults={'order': i + 1}
                )
                
                if module_created:
                    # Create sample video lessons
                    for j in range(3):
                        VideoLesson.objects.get_or_create(
                            module=module,
                            title=f'{module_title} - Lesson {j+1}',
                            defaults={
                                'youtube_video_id': f'sample_video_{i}_{j}',
                                'youtube_url': f'https://youtube.com/watch?v=sample_video_{i}_{j}',
                                'duration': 1800 + (j * 300),  # 30-45 minutes
                                'description': f'This is lesson {j+1} of {module_title}',
                                'order': j + 1,
                                'is_preview': j == 0,  # First lesson is preview
                            }
                        )
    
    # Create sample enrollments
    if students and courses:
        for i, student in enumerate(students[:3]):  # Enroll first 3 students
            course = courses[i % len(courses)]
            enrollment, created = Enrollment.objects.get_or_create(
                user=student,
                course=course,
                defaults={
                    'enrollment_type': 'purchased',
                    'total_amount': course.total_price,
                    'tax_amount': course.tax_amount,
                    'payment_status': 'partial' if i % 2 == 0 else 'completed',
                    'active': True,
                }
            )
            
            if created:
                print(f"Created enrollment: {student.name} -> {course.title}")
                
                # Create a payment
                Payment.objects.get_or_create(
                    enrollment=enrollment,
                    installment_number=1,
                    defaults={
                        'amount': course.total_price,
                        'tax_amount': course.tax_amount,
                        'payment_method': 'razorpay',
                        'due_date': date.today(),
                        'status': 'completed' if i % 2 == 1 else 'pending',
                        'payment_date': date.today() if i % 2 == 1 else None,
                        'transaction_id': f'txn_{i}_{course.id}' if i % 2 == 1 else None,
                    }
                )
    
    # Create email templates
    templates_data = [
        ('welcome_email', 'Welcome to CodeLearn LMS!', 
         '<h1>Welcome {{user_name}}!</h1><p>Thank you for joining CodeLearn LMS.</p>'),
        ('payment_confirmation', 'Payment Received - CodeLearn LMS',
         '<h1>Payment Confirmed</h1><p>Hi {{user_name}}, we have received your payment of ₹{{amount}}.</p>'),
        ('course_enrollment', 'Course Enrollment Confirmed',
         '<h1>Enrollment Confirmed</h1><p>You are now enrolled in {{course_title}}.</p>'),
    ]
    
    for name, subject, html_template in templates_data:
        EmailTemplate.objects.get_or_create(
            name=name,
            defaults={
                'subject': subject,
                'html_template': html_template,
                'is_active': True
            }
        )
    
    print("Sample data creation completed!")

if __name__ == '__main__':
    create_sample_data()