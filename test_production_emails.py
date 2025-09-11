#!/usr/bin/env python3
"""
Test script for production email sending with SendGrid
This script temporarily overrides email settings to test actual SendGrid delivery
"""
import os
import sys
import django

# Add the project directory to Python path
sys.path.append('/Users/jobinsebastian/djangoprojects/lms')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'codelearn_lms.settings')

# Setup Django
django.setup()

from django.conf import settings
from django.core.mail import send_mail
from django.contrib.auth import get_user_model
from emails.utils import EmailService

User = get_user_model()

def test_sendgrid_direct():
    """Test SendGrid API directly with production settings"""
    print("🔧 Testing SendGrid Direct API")
    
    # Check if we have a valid SendGrid API key
    api_key = settings.EMAIL_HOST_PASSWORD
    if not api_key or api_key == 'your-sendgrid-api-key':
        print("❌ SendGrid API key is not configured properly")
        print("   Please set EMAIL_HOST_PASSWORD in your environment or .env file")
        return False
    
    print(f"   API Key Preview: {api_key[:8]}...")
    
    # Temporarily override email backend to use SendGrid
    original_backend = settings.EMAIL_BACKEND
    settings.EMAIL_BACKEND = 'sendgrid_backend.SendgridBackend'
    
    try:
        # Test simple email sending
        result = send_mail(
            subject='Test Email from CodeLearn LMS',
            message='This is a test email to verify SendGrid configuration.',
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=['test@example.com'],  # Change this to your test email
            fail_silently=False,
        )
        
        if result:
            print("✅ Test email sent successfully via SendGrid")
        else:
            print("❌ Failed to send test email")
            
    except Exception as e:
        print(f"❌ Error sending via SendGrid: {str(e)}")
        return False
    finally:
        # Restore original backend
        settings.EMAIL_BACKEND = original_backend
    
    return True

def test_email_service_production():
    """Test EmailService with production SendGrid"""
    print("📧 Testing EmailService with Production SendGrid")
    
    # Check API key
    api_key = settings.EMAIL_HOST_PASSWORD
    if not api_key or api_key.startswith('your-'):
        print("❌ SendGrid API key not configured")
        return False
    
    try:
        email_service = EmailService()
        
        # Test sending a simple email
        result = email_service.send_email(
            to_email='test@example.com',  # Change this to your test email
            subject='CodeLearn LMS - Email Service Test',
            html_content='''
            <html>
            <body style="font-family: Arial, sans-serif;">
                <h2 style="color: #2C5F5F;">Email Service Test</h2>
                <p>This is a test email from CodeLearn LMS email service.</p>
                <p>If you received this, the email system is working correctly!</p>
                <p>Timestamp: {timestamp}</p>
            </body>
            </html>
            '''.format(timestamp=datetime.now().strftime('%Y-%m-%d %H:%M:%S')),
            text_content='Email Service Test - This is a test email from CodeLearn LMS.',
            to_name='Test User',
            template_type='test'
        )
        
        if result:
            print("✅ EmailService test email sent successfully")
        else:
            print("❌ EmailService failed to send email")
            
        return result
        
    except Exception as e:
        print(f"❌ EmailService error: {str(e)}")
        return False

def test_with_real_user_email():
    """Test with a real user email address"""
    print("👤 Testing with Real User Email")
    
    # Prompt for test email address
    test_email = input("Enter your email address for testing (or press Enter to skip): ").strip()
    
    if not test_email:
        print("   Skipped - no email address provided")
        return True
    
    try:
        email_service = EmailService()
        
        # Send test enrollment confirmation
        html_content = f'''
        <!DOCTYPE html>
        <html>
        <head>
            <style>
                body {{ font-family: Arial, sans-serif; }}
                .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                .header {{ background: #2C5F5F; color: white; padding: 20px; text-align: center; }}
                .content {{ padding: 20px; background: #f9f9f9; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>🎉 CodeLearn LMS Email Test</h1>
                </div>
                <div class="content">
                    <p>Hi there,</p>
                    <p>This is a test email from the CodeLearn LMS system to verify that:</p>
                    <ul>
                        <li>✅ SendGrid integration is working</li>
                        <li>✅ Email templates are rendering correctly</li>
                        <li>✅ Emails are being delivered successfully</li>
                    </ul>
                    <p>If you received this email, everything is working perfectly!</p>
                    <p><strong>Test Details:</strong></p>
                    <ul>
                        <li>Sent to: {test_email}</li>
                        <li>From: {settings.DEFAULT_FROM_EMAIL}</li>
                        <li>Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</li>
                    </ul>
                    <p>Best regards,<br>CodeLearn LMS Team</p>
                </div>
            </div>
        </body>
        </html>
        '''
        
        result = email_service.send_email(
            to_email=test_email,
            subject='CodeLearn LMS - Email System Test ✅',
            html_content=html_content,
            to_name='Test User',
            template_type='system_test'
        )
        
        if result:
            print(f"✅ Test email sent to {test_email}")
            print("   Check your inbox (and spam folder) for the test email")
        else:
            print(f"❌ Failed to send test email to {test_email}")
            
        return result
        
    except Exception as e:
        print(f"❌ Error sending to real email: {str(e)}")
        return False

def main():
    """Main test function"""
    print("🚀 Production Email Testing with SendGrid")
    print("=" * 50)
    
    from datetime import datetime
    
    # Show current configuration
    print(f"📝 Current Configuration:")
    print(f"   EMAIL_BACKEND: {settings.EMAIL_BACKEND}")
    print(f"   EMAIL_HOST: {settings.EMAIL_HOST}")
    print(f"   EMAIL_HOST_USER: {settings.EMAIL_HOST_USER}")
    print(f"   DEFAULT_FROM_EMAIL: {settings.DEFAULT_FROM_EMAIL}")
    
    api_key = settings.EMAIL_HOST_PASSWORD
    if api_key:
        print(f"   API Key Preview: {api_key[:8]}...")
    else:
        print("   ❌ API Key: Not configured")
    print()
    
    # Check if SendGrid backend is available
    try:
        import sendgrid_backend
        print("✅ SendGrid backend is available")
    except ImportError:
        print("❌ SendGrid backend not installed")
        print("   Install with: pip install django-sendgrid-v5")
        return
    
    # Test 1: Direct SendGrid
    test_sendgrid_direct()
    print()
    
    # Test 2: EmailService
    test_email_service_production()
    print()
    
    # Test 3: Real email test
    test_with_real_user_email()
    print()
    
    print("=" * 50)
    print("📋 Production Checklist:")
    print("   □ Set EMAIL_BACKEND to 'sendgrid_backend.SendgridBackend' in production")
    print("   □ Configure EMAIL_HOST_PASSWORD with your SendGrid API key")
    print("   □ Verify SendGrid domain authentication")
    print("   □ Test with real email addresses")
    print("   □ Monitor SendGrid dashboard for delivery status")
    print("   □ Set up email templates in production database")

if __name__ == "__main__":
    main()