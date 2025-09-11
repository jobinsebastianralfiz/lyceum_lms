#!/usr/bin/env python
"""
Test script to demonstrate improved login error messages
"""
import os
import sys
import django
import requests
import json

# Add the project root to Python path
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_root)

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'codelearn_lms.settings')
django.setup()

def test_login_errors():
    """Test various login error scenarios"""
    base_url = "http://localhost:8000/api/users/auth/login/"
    
    test_cases = [
        {
            "name": "Missing Email",
            "data": {"password": "testpass123"},
            "expected_field": "email"
        },
        {
            "name": "Missing Password", 
            "data": {"email": "test@example.com"},
            "expected_field": "password"
        },
        {
            "name": "Non-existent Email",
            "data": {"email": "nonexistent@example.com", "password": "testpass123"},
            "expected_field": "email"
        },
        {
            "name": "Incorrect Password",
            "data": {"email": "existing@example.com", "password": "wrongpassword"}, 
            "expected_field": "password"
        }
    ]
    
    print("Testing Login API Error Messages")
    print("=" * 50)
    
    for test_case in test_cases:
        print(f"\n🧪 Test: {test_case['name']}")
        print(f"📤 Data: {test_case['data']}")
        
        try:
            response = requests.post(base_url, json=test_case['data'])
            print(f"📊 Status: {response.status_code}")
            
            if response.status_code == 400:
                error_data = response.json()
                print(f"✅ Response: {json.dumps(error_data, indent=2)}")
                
                expected_field = test_case['expected_field']
                if expected_field in error_data:
                    print(f"✅ Expected field '{expected_field}' found in errors")
                else:
                    print(f"❌ Expected field '{expected_field}' NOT found in errors")
            else:
                print(f"📄 Response: {response.text}")
                
        except requests.exceptions.ConnectionError:
            print("❌ Cannot connect to server. Make sure Django is running on localhost:8000")
        except Exception as e:
            print(f"❌ Error: {str(e)}")
        
        print("-" * 30)

if __name__ == "__main__":
    test_login_errors()