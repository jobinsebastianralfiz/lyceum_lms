#!/usr/bin/env python
"""
Simple script to test admin functionality and generate sample data
"""
import os
import sys
import django

# Setup Django
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'codelearn_lms.settings')
django.setup()

from apps.users.models import User, Team, TeamMembership
from apps.courses.models import Course, Category
from apps.payments.models import Enrollment

def create_sample_data():
    print("🔄 Creating sample data for dashboard...")
    
    # Create admin user if doesn't exist
    admin_user, created = User.objects.get_or_create(
        email='admin@codelearn.com',
        defaults={
            'name': 'Admin User',
            'role': 'admin',
            'username': 'admin',
            'is_staff': True,
            'is_superuser': True
        }
    )
    if created:
        admin_user.set_password('admin123')
        admin_user.save()
        print(f"✅ Created admin user: {admin_user.email}")
    else:
        print(f"✅ Admin user exists: {admin_user.email}")
    
    # Create sample students
    students = []
    for i in range(10):
        user, created = User.objects.get_or_create(
            email=f'student{i+1}@test.com',
            defaults={
                'name': f'Student {i+1}',
                'role': 'student',
                'username': f'student{i+1}'
            }
        )
        students.append(user)
        if created:
            user.set_password('password123')
            user.save()
    
    print(f"✅ Created {len(students)} students")
    
    # Create sample category and courses
    category, _ = Category.objects.get_or_create(
        name='Programming',
        defaults={'description': 'Programming courses'}
    )
    
    courses = []
    course_names = ['Python Basics', 'Django Advanced', 'JavaScript Fundamentals', 'React Development']
    for name in course_names:
        course, created = Course.objects.get_or_create(
            title=name,
            defaults={
                'description': f'Learn {name} from scratch',
                'category': category,
                'price': 2999.00 if 'Advanced' in name else 1999.00,
                'is_published': True,
                'created_by': admin_user
            }
        )
        courses.append(course)
    
    print(f"✅ Created {len(courses)} courses")
    
    # Create sample teams
    teams = []
    team_names = ['Python Developers', 'Web Development Squad', 'Data Science Team']
    for i, name in enumerate(team_names):
        team, created = Team.objects.get_or_create(
            name=name,
            defaults={
                'description': f'{name} collaborative learning',
                'max_members': 4,
                'team_leader': students[i],
                'created_by': admin_user
            }
        )
        teams.append(team)
        
        # Add members to teams
        for j in range(3):
            student_idx = (i * 3 + j) % len(students)
            TeamMembership.objects.get_or_create(
                team=team,
                user=students[student_idx],
                defaults={'role': 'leader' if j == 0 else 'member'}
            )
    
    print(f"✅ Created {len(teams)} teams with members")
    
    # Create sample enrollments
    enrollments = []
    for i, student in enumerate(students[:8]):
        course = courses[i % len(courses)]
        enrollment, created = Enrollment.objects.get_or_create(
            user=student,
            course=course,
            defaults={
                'enrollment_type': 'individual',
                'total_amount': course.price,
                'payment_status': 'completed' if i % 3 == 0 else 'pending'
            }
        )
        enrollments.append(enrollment)
    
    # Create team enrollments
    for i, team in enumerate(teams):
        course = courses[i % len(courses)]
        enrollment, created = Enrollment.objects.get_or_create(
            user=team.team_leader,
            course=course,
            team=team,
            defaults={
                'enrollment_type': 'team',
                'total_amount': course.price,
                'payment_status': 'completed'
            }
        )
        enrollments.append(enrollment)
    
    print(f"✅ Created {len(enrollments)} enrollments")
    
    print("\n🎉 Sample data creation completed!")
    print(f"📊 Dashboard Statistics:")
    print(f"   - Students: {User.objects.filter(role='student').count()}")
    print(f"   - Courses: {Course.objects.filter(is_published=True).count()}")
    print(f"   - Teams: {Team.objects.filter(is_active=True).count()}")
    print(f"   - Enrollments: {Enrollment.objects.filter(active=True).count()}")
    print(f"\n🔐 Admin Login:")
    print(f"   URL: http://localhost:8000/admin/")
    print(f"   Email: admin@codelearn.com")
    print(f"   Password: admin123")

if __name__ == '__main__':
    create_sample_data()