#!/usr/bin/env python
import os
import django
from django.contrib.auth import get_user_model

# Setup Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'codelearn_lms.settings')
django.setup()

User = get_user_model()

# Create superuser
username = 'ralffmqq'
email = 'info@uptrail.com'
password = 'mkagmca021#'

if not User.objects.filter(username=username).exists():
    user = User.objects.create_superuser(username=username, email=email, password=password)
    user.role = 'admin'  # Set role to admin for mentor dashboard access
    user.save()
    print(f"Superuser created successfully!")
    print(f"Username: {username}")
    print(f"Email: {email}")
    print(f"Password: {password}")
    print(f"Role: {user.role}")
else:
    user = User.objects.get(username=username)
    print(f"Superuser '{username}' already exists!")
    print(f"Username: {username}")
    print(f"Password: {password}")
    print(f"Current role: {user.role}")
    
    # Update role if it's not admin
    if user.role != 'admin':
        user.role = 'admin'
        user.save()
        print(f"Role updated to: {user.role}")