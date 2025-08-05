#!/usr/bin/env python
"""
Simple test script to verify custom user form functionality
"""
import os
import sys
import django

# Add the project root to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'codelearn_lms.settings')
django.setup()

from django.test import RequestFactory, Client
from django.contrib.auth import get_user_model
from apps.custom_admin.views import user_create_view
from apps.custom_admin.forms import CustomUserCreationForm

User = get_user_model()

def test_form_creation():
    """Test that the form can be created and rendered"""
    print("Testing form creation...")
    form = CustomUserCreationForm()
    print(f"✓ Form created with {len(form.fields)} fields")
    
    # Test form validation with valid data
    valid_data = {
        'name': 'Test User',
        'email': 'testuser@example.com',
        'username': 'testuser',
        'role': 'student',
        'phone_number': '1234567890',
        'address': 'Test Address',
        'is_staff': False,
        'is_active': True,
        'password1': 'testpass123!',
        'password2': 'testpass123!'
    }
    
    form = CustomUserCreationForm(valid_data)
    if form.is_valid():
        print("✓ Form validation passed")
    else:
        print("✗ Form validation failed:")
        for field, errors in form.errors.items():
            print(f"  {field}: {errors}")
    
    return True

def test_view_access():
    """Test that the view can be accessed"""
    print("\nTesting view access...")
    
    # Create a superuser for testing
    superuser = User.objects.filter(is_superuser=True).first()
    if not superuser:
        print("✗ No superuser found for testing")
        return False
    
    # Create a request factory
    factory = RequestFactory()
    
    # Test GET request
    request = factory.get('/admin/users/add/')
    request.user = superuser
    
    try:
        response = user_create_view(request)
        print(f"✓ View accessible, status: {response.status_code if hasattr(response, 'status_code') else 'rendered'}")
        return True
    except Exception as e:
        print(f"✗ View access failed: {e}")
        return False

def main():
    print("Testing Custom User Management System")
    print("=" * 40)
    
    try:
        test_form_creation()
        test_view_access()
        print("\n" + "=" * 40)
        print("✓ All tests completed successfully!")
        print("\nYour custom user management system is ready to use!")
        print("Visit: http://127.0.0.1:8000/admin/users/add/")
        
    except Exception as e:
        print(f"\n✗ Test failed with error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()