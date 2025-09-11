#!/usr/bin/env python3
"""
Test script for email system functionality
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
from django.contrib.auth import get_user_model
from apps.courses.models import Course
from apps.payments.models import Enrollment, Payment, TaxInvoice
from emails.utils import EmailService, send_verification_email, send_enrollment_confirmation_email
from emails.invoice_generator import generate_invoice_pdf
from decimal import Decimal
import traceback

User = get_user_model()

def test_email_configuration():
    """Test basic email configuration"""
    print("🔧 Testing Email Configuration")
    print(f"   EMAIL_BACKEND: {settings.EMAIL_BACKEND}")
    print(f"   EMAIL_HOST: {settings.EMAIL_HOST}")
    print(f"   EMAIL_PORT: {settings.EMAIL_PORT}")
    print(f"   EMAIL_USE_TLS: {settings.EMAIL_USE_TLS}")
    print(f"   EMAIL_HOST_USER: {settings.EMAIL_HOST_USER}")
    print(f"   EMAIL_HOST_PASSWORD: {'✅ Set' if settings.EMAIL_HOST_PASSWORD else '❌ Missing'}")
    print(f"   DEFAULT_FROM_EMAIL: {settings.DEFAULT_FROM_EMAIL}")
    
    if settings.EMAIL_HOST_PASSWORD and len(settings.EMAIL_HOST_PASSWORD) > 10:
        print(f"   SendGrid API Key Preview: {settings.EMAIL_HOST_PASSWORD[:8]}...")
    
    print()

def test_sendgrid_service():
    """Test SendGrid service initialization"""
    print("📧 Testing SendGrid Service")
    try:
        email_service = EmailService()
        print("✅ EmailService initialized successfully")
        print(f"   From Email: {email_service.from_email}")
        return email_service
    except Exception as e:
        print(f"❌ EmailService initialization failed: {str(e)}")
        traceback.print_exc()
        return None

def test_verification_email():
    """Test verification email sending"""
    print("✉️  Testing Verification Email")
    
    # Try to find a test user or create one
    try:
        test_user = User.objects.filter(email__icontains='test').first()
        if not test_user:
            print("   No test user found, creating one...")
            test_user = User.objects.create_user(
                username='test_email_user',
                email='test@example.com',
                name='Test Email User',
                password='testpassword123'
            )
            print(f"   Created test user: {test_user.email}")
        else:
            print(f"   Using existing test user: {test_user.email}")
        
        # Send verification email
        result = send_verification_email(test_user)
        if result:
            print("✅ Verification email sent successfully")
        else:
            print("❌ Failed to send verification email")
        
        return test_user
        
    except Exception as e:
        print(f"❌ Error testing verification email: {str(e)}")
        traceback.print_exc()
        return None

def test_enrollment_email():
    """Test enrollment confirmation email with invoice"""
    print("🎓 Testing Enrollment Confirmation Email")
    
    try:
        # Find or create test data
        test_user = User.objects.filter(email__icontains='test').first()
        if not test_user:
            test_user = User.objects.create_user(
                username='test_enrollment_user',
                email='test_enrollment@example.com',
                name='Test Enrollment User',
                password='testpassword123'
            )
        
        test_course = Course.objects.first()
        if not test_course:
            print("❌ No courses found for testing")
            return False
        
        print(f"   Using course: {test_course.title}")
        print(f"   Course price: ₹{test_course.price}")
        
        # Check if enrollment already exists
        existing_enrollment = Enrollment.objects.filter(user=test_user, course=test_course).first()
        if existing_enrollment:
            enrollment = existing_enrollment
            print(f"   Using existing enrollment: {enrollment.id}")
        else:
            # Create test enrollment
            enrollment = Enrollment.objects.create(
                user=test_user,
                course=test_course,
                total_amount=test_course.price,
                tax_amount=test_course.price * Decimal('0.18'),
                payment_status='completed'
            )
            print(f"   Created test enrollment: {enrollment.id}")
            
            # Create test payment
            from datetime import date
            payment = Payment.objects.create(
                enrollment=enrollment,
                amount=test_course.price,
                tax_amount=test_course.price * Decimal('0.18'),
                payment_method='test',
                transaction_id='test_' + str(enrollment.id),
                status='completed',
                due_date=date.today()
            )
            print(f"   Created test payment: {payment.id}")
        
        # Test enrollment email without invoice first
        print("   Testing enrollment email without invoice...")
        result = send_enrollment_confirmation_email(enrollment, include_invoice=False)
        if result:
            print("✅ Enrollment email (no invoice) sent successfully")
        else:
            print("❌ Failed to send enrollment email (no invoice)")
        
        # Test with invoice if we have a paid course
        if test_course.price > 0:
            print("   Testing enrollment email with invoice...")
            
            # Create or get tax invoice
            tax_invoice = TaxInvoice.objects.filter(enrollment=enrollment).first()
            if not tax_invoice:
                payment = Payment.objects.filter(enrollment=enrollment).first()
                if payment:
                    tax_invoice = TaxInvoice.objects.create(
                        enrollment=enrollment,
                        payment=payment,
                        invoice_number=f"TEST-INV-{enrollment.id}",
                        subtotal=test_course.price,
                        tax_rate=18.0,
                        tax_amount=test_course.price * Decimal('0.18'),
                        total_amount=test_course.price * Decimal('1.18')
                    )
            
            if tax_invoice:
                # Generate PDF
                invoice_pdf = generate_invoice_pdf(tax_invoice)
                print(f"   Generated PDF invoice ({len(invoice_pdf)} bytes)")
                
                # Send email with invoice
                result = send_enrollment_confirmation_email(
                    enrollment, 
                    include_invoice=True, 
                    invoice_pdf_content=invoice_pdf
                )
                if result:
                    print("✅ Enrollment email (with invoice) sent successfully")
                else:
                    print("❌ Failed to send enrollment email (with invoice)")
            else:
                print("   Could not create tax invoice for testing")
        
        return True
        
    except Exception as e:
        print(f"❌ Error testing enrollment email: {str(e)}")
        traceback.print_exc()
        return False

def test_pdf_generation():
    """Test PDF invoice generation"""
    print("📄 Testing PDF Invoice Generation")
    
    try:
        # Find a tax invoice to test with
        tax_invoice = TaxInvoice.objects.first()
        if not tax_invoice:
            print("   No tax invoices found for testing")
            return False
        
        print(f"   Using tax invoice: {tax_invoice.invoice_number}")
        
        # Generate PDF
        pdf_content = generate_invoice_pdf(tax_invoice)
        print(f"✅ PDF generated successfully ({len(pdf_content)} bytes)")
        
        # Save test PDF
        with open('/Users/jobinsebastian/djangoprojects/lms/test_invoice.pdf', 'wb') as f:
            f.write(pdf_content)
        print("   Test PDF saved as test_invoice.pdf")
        
        return True
        
    except Exception as e:
        print(f"❌ Error generating PDF: {str(e)}")
        traceback.print_exc()
        return False

def main():
    """Run all email tests"""
    print("🚀 Email System Test Suite")
    print("=" * 50)
    
    # Test configuration
    test_email_configuration()
    
    # Test SendGrid service
    email_service = test_sendgrid_service()
    if not email_service:
        print("❌ Cannot continue without working email service")
        return
    
    print()
    
    # Test PDF generation
    test_pdf_generation()
    print()
    
    # Test verification email
    test_user = test_verification_email()
    print()
    
    # Test enrollment email
    test_enrollment_email()
    print()
    
    print("=" * 50)
    print("✅ Email system testing completed!")
    print()
    print("💡 Tips for production:")
    print("   1. Make sure SENDGRID_API_KEY is set correctly")
    print("   2. Verify your SendGrid domain authentication")
    print("   3. Check SendGrid activity logs for delivery status")
    print("   4. Test with real email addresses you control")

if __name__ == "__main__":
    main()