#!/usr/bin/env python
import os
import django
from django.contrib.auth import get_user_model

# Setup Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'codelearn_lms.settings')
django.setup()

User = get_user_model()

# Create superuser
username = 'admin'
email = 'admin@codelearn.com'
password = 'admin123'

if not User.objects.filter(username=username).exists():
    User.objects.create_superuser(username=username, email=email, password=password)
    print(f"Superuser created successfully!")
    print(f"Username: {username}")
    print(f"Email: {email}")
    print(f"Password: {password}")
else:
    print(f"Superuser '{username}' already exists!")
    print(f"Username: {username}")
    print(f"Password: {password}")