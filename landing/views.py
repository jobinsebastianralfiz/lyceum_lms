import json
import razorpay
import requests
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib.auth import get_user_model, authenticate, login
from django.contrib.auth.forms import UserCreationForm
from django.contrib import messages
from django.conf import settings
from django.db import transaction
from django.http import JsonResponse, HttpResponseBadRequest
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from django.utils import timezone
from django import forms

from apps.courses.models import Course, Category
from apps.payments.models import Enrollment, Payment
from apps.ratings.models import CourseRating

User = get_user_model()

# Helper function to verify Cloudflare Turnstile
def verify_turnstile(token, remote_ip=None):
    """
    Verify Cloudflare Turnstile response
    Returns (success: bool, error_message: str)
    """
    # Skip verification if Turnstile is not configured
    turnstile_secret = getattr(settings, 'CLOUDFLARE_TURNSTILE_SECRET_KEY', '')
    if not turnstile_secret or turnstile_secret == 'your-turnstile-secret-key':
        # In development, if Turnstile is not configured, skip verification
        if settings.DEBUG:
            return True, None
        return False, 'Turnstile verification is not configured.'

    # Verify the token with Cloudflare
    verify_url = getattr(settings, 'CLOUDFLARE_TURNSTILE_VERIFY_URL', 'https://challenges.cloudflare.com/turnstile/v0/siteverify')

    data = {
        'secret': turnstile_secret,
        'response': token,
    }

    if remote_ip:
        data['remoteip'] = remote_ip

    try:
        response = requests.post(verify_url, data=data, timeout=10)
        result = response.json()

        if result.get('success'):
            return True, None
        else:
            error_codes = result.get('error-codes', [])
            return False, f'Verification failed: {", ".join(error_codes)}'
    except requests.RequestException as e:
        return False, f'Verification request failed: {str(e)}'
    except Exception as e:
        return False, f'Verification error: {str(e)}'

# Custom registration form
class PublicUserRegistrationForm(UserCreationForm):
    email = forms.EmailField(
        required=True,
        widget=forms.EmailInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter your email'
        })
    )
    name = forms.CharField(
        max_length=100,
        required=True,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter your full name'
        })
    )
    phone = forms.CharField(
        max_length=15,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter your phone number (optional)'
        })
    )
    
    class Meta:
        model = User
        fields = ('username', 'name', 'email', 'phone', 'password1', 'password2')
        widgets = {
            'username': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Choose a username'
            })
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['password1'].widget.attrs.update({
            'class': 'form-control',
            'placeholder': 'Create a password'
        })
        self.fields['password2'].widget.attrs.update({
            'class': 'form-control',
            'placeholder': 'Confirm your password'
        })
    
    def clean_email(self):
        email = self.cleaned_data.get('email')
        if User.objects.filter(email=email).exists():
            raise forms.ValidationError("A user with this email already exists.")
        return email
    
    def save(self, commit=True):
        user = super().save(commit=False)
        user.email = self.cleaned_data['email']
        user.name = self.cleaned_data['name']
        if self.cleaned_data.get('phone'):
            user.phone_number = self.cleaned_data['phone']
        if commit:
            user.save()
        return user


def home(request):
    """Landing page view with featured courses"""
    courses = Course.objects.filter(
        is_published=True, 
        allow_public_enrollment=True
    ).order_by('-created_at')[:6]  # Get featured courses
    
    context = {
        'courses': courses,
    }
    return render(request, 'landing/home.html', context)

def privacy_policy(request):
    """Privacy policy page view"""
    return render(request, 'landing/privacy_policy.html')

def terms_conditions(request):
    """Terms and conditions page view"""
    return render(request, 'landing/terms_conditions.html')

def register(request):
    """Public user registration with email verification"""
    if request.user.is_authenticated:
        return redirect('landing:home')

    if request.method == 'POST':
        # Verify Cloudflare Turnstile
        turnstile_response = request.POST.get('cf-turnstile-response', '')
        if turnstile_response:
            remote_ip = request.META.get('REMOTE_ADDR')
            is_valid, error_message = verify_turnstile(turnstile_response, remote_ip)
            if not is_valid:
                messages.error(request, f'Security verification failed. Please try again. {error_message or ""}')
                context = {
                    'CLOUDFLARE_TURNSTILE_SITE_KEY': getattr(settings, 'CLOUDFLARE_TURNSTILE_SITE_KEY', '')
                }
                return render(request, 'landing/register.html', context)

        # Handle form data manually for new template
        email = request.POST.get('email')
        first_name = request.POST.get('first_name', '')
        last_name = request.POST.get('last_name', '')
        phone = request.POST.get('phone', '')
        password1 = request.POST.get('password1')
        password2 = request.POST.get('password2')

        # Basic validation
        if not all([email, first_name, password1, password2]):
            messages.error(request, 'Please fill in all required fields.')
            context = {
                'CLOUDFLARE_TURNSTILE_SITE_KEY': getattr(settings, 'CLOUDFLARE_TURNSTILE_SITE_KEY', '')
            }
            return render(request, 'landing/register.html', context)

        if password1 != password2:
            messages.error(request, 'Passwords do not match.')
            context = {
                'CLOUDFLARE_TURNSTILE_SITE_KEY': getattr(settings, 'CLOUDFLARE_TURNSTILE_SITE_KEY', '')
            }
            return render(request, 'landing/register.html', context)

        if User.objects.filter(email=email).exists():
            messages.error(request, 'A user with this email already exists.')
            context = {
                'CLOUDFLARE_TURNSTILE_SITE_KEY': getattr(settings, 'CLOUDFLARE_TURNSTILE_SITE_KEY', '')
            }
            return render(request, 'landing/register.html', context)

        try:
            # Create user
            username = email.split('@')[0]  # Use email prefix as username
            counter = 1
            original_username = username
            while User.objects.filter(username=username).exists():
                username = f"{original_username}{counter}"
                counter += 1

            user = User.objects.create_user(
                username=username,
                email=email,
                password=password1,
                name=f"{first_name} {last_name}".strip(),
                phone_number=phone
            )

            # Send verification email
            from emails.utils import send_verification_email
            try:
                if send_verification_email(user):
                    messages.success(request, f'Account created successfully! Please check your email to verify your account before logging in.')
                else:
                    messages.warning(request, f'Account created successfully! However, there was an issue sending the verification email. You can still log in.')
            except Exception as e:
                messages.warning(request, f'Account created successfully! There was an issue sending the verification email, but you can still log in.')

            return redirect('landing:login')

        except Exception as e:
            messages.error(request, f'Error creating account: {str(e)}')

    context = {
        'CLOUDFLARE_TURNSTILE_SITE_KEY': getattr(settings, 'CLOUDFLARE_TURNSTILE_SITE_KEY', '')
    }
    return render(request, 'landing/register.html', context)


def login_view(request):
    """User login view"""
    if request.user.is_authenticated:
        # Redirect authenticated users to appropriate dashboard
        if request.user.is_staff:
            return redirect('custom_admin:dashboard')
        else:
            return redirect('student_portal:dashboard')

    if request.method == 'POST':
        # Verify Cloudflare Turnstile
        turnstile_response = request.POST.get('cf-turnstile-response', '')
        if turnstile_response:
            remote_ip = request.META.get('REMOTE_ADDR')
            is_valid, error_message = verify_turnstile(turnstile_response, remote_ip)
            if not is_valid:
                messages.error(request, f'Security verification failed. Please try again. {error_message or ""}')
                context = {
                    'CLOUDFLARE_TURNSTILE_SITE_KEY': getattr(settings, 'CLOUDFLARE_TURNSTILE_SITE_KEY', '')
                }
                return render(request, 'landing/login.html', context)

        email_or_username = request.POST.get('email', '').strip()
        password = request.POST.get('password', '')

        if not email_or_username or not password:
            messages.error(request, 'Please provide both email/username and password.')
            context = {
                'CLOUDFLARE_TURNSTILE_SITE_KEY': getattr(settings, 'CLOUDFLARE_TURNSTILE_SITE_KEY', '')
            }
            return render(request, 'landing/login.html', context)

        # Try to authenticate by username first
        user = authenticate(request, username=email_or_username, password=password)

        # If that fails, try to find user by email and authenticate
        if not user:
            try:
                user_obj = User.objects.get(email=email_or_username)
                user = authenticate(request, username=user_obj.username, password=password)
            except User.DoesNotExist:
                user = None

        if user:
            login(request, user)

            # Handle next parameter for redirects
            next_url = request.POST.get('next') or request.GET.get('next')
            if next_url:
                return redirect(next_url)

            # Redirect based on user type
            if user.is_staff:
                messages.success(request, f'Welcome back, {user.get_full_name() or user.username}!')
                return redirect('custom_admin:dashboard')
            else:
                messages.success(request, f'Welcome back, {user.get_full_name() or user.username}!')
                return redirect('student_portal:dashboard')
        else:
            messages.error(request, 'Invalid email/username or password. Please try again.')

    context = {
        'CLOUDFLARE_TURNSTILE_SITE_KEY': getattr(settings, 'CLOUDFLARE_TURNSTILE_SITE_KEY', '')
    }
    return render(request, 'landing/login.html', context)


def courses(request):
    """Public courses listing page with categories"""
    courses = Course.objects.filter(
        is_published=True,
        allow_public_enrollment=True
    ).select_related('category').order_by('-created_at')
    
    categories = Category.objects.filter(
        courses__is_published=True,
        courses__allow_public_enrollment=True
    ).distinct().order_by('name')
    
    context = {
        'courses': courses,
        'categories': categories,
    }
    return render(request, 'landing/courses.html', context)

def course_detail(request, course_id):
    """Public course detail page for enrollment"""
    course = get_object_or_404(
        Course, 
        id=course_id, 
        is_published=True, 
        allow_public_enrollment=True
    )
    
    # Check if user is already enrolled
    is_enrolled = False
    user_rating = None
    
    if request.user.is_authenticated:
        is_enrolled = Enrollment.objects.filter(
            user=request.user, 
            course=course, 
            active=True
        ).exists()
        
        # Get user's rating for this course
        user_rating = CourseRating.objects.filter(
            course=course,
            user=request.user
        ).first()
    
    context = {
        'course': course,
        'is_enrolled': is_enrolled,
        'user_rating': user_rating,
        'razorpay_key': getattr(settings, 'RAZORPAY_KEY_ID', ''),
    }
    return render(request, 'landing/course_detail.html', context)

def enroll_course(request, course_id):
    """Handle course enrollment with payment"""
    print(f"=== ENROLLMENT DEBUG START ===")
    print(f"User: {request.user}")
    print(f"Is authenticated: {request.user.is_authenticated}")
    print(f"Request method: {request.method}")
    print(f"Course ID: {course_id}")
    
    # Check authentication first
    if not request.user.is_authenticated:
        messages.error(request, 'You must be logged in to enroll in a course.')
        return redirect('landing:login')
    
    try:
        course = get_object_or_404(
            Course, 
            id=course_id, 
            is_published=True, 
            allow_public_enrollment=True
        )
        
        # Debug logging
        print(f"DEBUG: User {request.user.email} attempting to enroll in course {course.title}")
        print(f"DEBUG: Course is_published: {course.is_published}")
        print(f"DEBUG: Course allow_public_enrollment: {course.allow_public_enrollment}")
        print(f"DEBUG: Course is_free_course: {course.is_free_course}")
        print(f"DEBUG: Course total_price: {course.total_price}")
        
        # Security check: prevent duplicate enrollments
        existing_enrollment = Enrollment.objects.filter(user=request.user, course=course, active=True)
        print(f"DEBUG: Checking existing enrollments: {existing_enrollment.count()} found")
        if existing_enrollment.exists():
            messages.warning(request, 'You are already enrolled in this course.')
            print(f"DEBUG: User already enrolled")
            return redirect('landing:course_detail', course_id=course.id)
        
        print(f"DEBUG: About to check request method: {request.method}")
        if request.method == 'POST':
            print(f"DEBUG: Processing POST request for enrollment")
            if course.is_free_course:
                print(f"DEBUG: Processing free course enrollment")
                # Free course enrollment
                with transaction.atomic():
                    enrollment = Enrollment.objects.create(
                        user=request.user,
                        course=course,
                        enrollment_type='individual',
                        total_amount=0,
                        tax_amount=0,
                        payment_status='free'
                    )
                    messages.success(request, f'Successfully enrolled in {course.title}!')
                    return redirect('student_portal:dashboard')
            else:
                print(f"DEBUG: Processing paid course enrollment")
                
                # Check if Razorpay keys are configured
                razorpay_key = getattr(settings, 'RAZORPAY_KEY_ID', '')
                razorpay_secret = getattr(settings, 'RAZORPAY_KEY_SECRET', '')
                
                print(f"DEBUG: Razorpay key length: {len(razorpay_key)}, secret length: {len(razorpay_secret)}")
                print(f"DEBUG: Key starts with: {razorpay_key[:8] if razorpay_key else 'EMPTY'}")
                print(f"DEBUG: Key full value: {razorpay_key}")
                print(f"DEBUG: Secret full value: {razorpay_secret[:10]}...")  # Only show first 10 chars of secret
                
                if not razorpay_key or not razorpay_secret or razorpay_key == 'your-razorpay-key-id':
                    messages.error(request, 'Payment system not configured. Please add your actual Razorpay keys to the .env file, or test with a free course.')
                    print(f"ERROR: Razorpay keys not configured - Key: {'PLACEHOLDER' if razorpay_key == 'your-razorpay-key-id' else ('SET' if razorpay_key else 'MISSING')}")
                    
                    # For testing - show link to create free course
                    messages.info(request, 'To test enrollment immediately, create a free course (set price = 0) in the admin panel.')
                    return redirect('landing:course_detail', course_id=course.id)
                
                # Paid course - create Razorpay order
                try:
                    # Initialize Razorpay client
                    client = razorpay.Client(auth=(razorpay_key, razorpay_secret))
                    
                    # Convert amount to paisa (multiply by 100)
                    amount_in_paisa = int(course.total_price * 100)
                    
                    # Create order
                    order_data = {
                        'amount': amount_in_paisa,
                        'currency': 'INR',
                        'receipt': f'course_{course.id}_user_{request.user.id}',
                        'notes': {
                            'course_id': course.id,
                            'user_id': request.user.id,
                            'enrollment_type': 'individual'
                        }
                    }
                    
                    razorpay_order = client.order.create(data=order_data)
                    
                    context = {
                        'course': course,
                        'razorpay_order_id': razorpay_order['id'],
                        'razorpay_key': getattr(settings, 'RAZORPAY_KEY_ID', ''),
                        'amount': amount_in_paisa,
                        'user_name': request.user.get_full_name() or request.user.username,
                        'user_email': request.user.email,
                    }
                    
                    try:
                        return render(request, 'landing/payment.html', context)
                    except Exception as template_error:
                        # Fallback: redirect with payment data as GET parameters for debugging
                        messages.error(request, f'Payment page error: {str(template_error)}')
                        return redirect('landing:course_detail', course_id=course.id)
                    
                except Exception as e:
                    messages.error(request, f'Payment initialization failed: {str(e)}')
                    print(f"ERROR: Payment initialization failed: {str(e)}")
                    return redirect('landing:course_detail', course_id=course.id)
        else:
            print(f"DEBUG: Request method is {request.method}, not POST")
            messages.info(request, f'Please use the enrollment form to enroll. (Request method: {request.method})')
    
    except Exception as e:
        messages.error(request, f'Enrollment error: {str(e)}')
        print(f"ERROR: Enrollment exception: {str(e)}")
        
    # If we reach here, something went wrong
    messages.warning(request, 'Enrollment request received but no action was taken. Please check if you are logged in and the course allows enrollment.')
    print(f"WARNING: Enrollment function reached end without processing - User: {request.user}, Method: {request.method}")
    print(f"=== ENROLLMENT DEBUG END ===")
    return redirect('landing:course_detail', course_id=course.id)

@csrf_exempt
@require_POST
def payment_success(request):
    """Handle successful payment callback from Razorpay"""
    print(f"=== PAYMENT SUCCESS DEBUG START ===")
    try:
        # Get payment details from request
        payment_id = request.POST.get('razorpay_payment_id')
        order_id = request.POST.get('razorpay_order_id')
        signature = request.POST.get('razorpay_signature')
        
        print(f"Payment ID: {payment_id}")
        print(f"Order ID: {order_id}")
        print(f"Signature received: {signature is not None}")
        
        if not all([payment_id, order_id, signature]):
            print("ERROR: Missing payment parameters")
            return HttpResponseBadRequest('Missing payment parameters')
        
        # Initialize Razorpay client
        razorpay_key = getattr(settings, 'RAZORPAY_KEY_ID', '')
        razorpay_secret = getattr(settings, 'RAZORPAY_KEY_SECRET', '')
        print(f"Razorpay Key: {razorpay_key[:10]}...")
        print(f"Razorpay Secret: {razorpay_secret[:10]}...")
        
        client = razorpay.Client(auth=(razorpay_key, razorpay_secret))
        
        # Verify payment signature
        params_dict = {
            'razorpay_order_id': order_id,
            'razorpay_payment_id': payment_id,
            'razorpay_signature': signature
        }
        
        print("Attempting signature verification...")
        try:
            client.utility.verify_payment_signature(params_dict)
            print("Signature verification successful!")
        except razorpay.errors.SignatureVerificationError as e:
            print(f"Signature verification failed: {str(e)}")
            return JsonResponse({'status': 'error', 'message': 'Invalid payment signature'})
        except Exception as e:
            print(f"Unexpected error during signature verification: {str(e)}")
            return JsonResponse({'status': 'error', 'message': f'Verification error: {str(e)}'})
        
        # Fetch order details to get course and user info
        print("Fetching order details...")
        try:
            order_details = client.order.fetch(order_id)
            print(f"Order details: {order_details}")
            
            course_id = order_details['notes']['course_id']
            user_id = order_details['notes']['user_id']
            print(f"Course ID from order: {course_id}")
            print(f"User ID from order: {user_id}")
        except Exception as e:
            print(f"Error fetching order details: {str(e)}")
            return JsonResponse({'status': 'error', 'message': f'Order fetch error: {str(e)}'})
        
        # Get course and user objects
        course = get_object_or_404(Course, id=course_id)
        user = get_object_or_404(User, id=user_id)
        
        # Security check: prevent duplicate enrollments
        if Enrollment.objects.filter(user=user, course=course, active=True).exists():
            return JsonResponse({'status': 'error', 'message': 'Already enrolled'})
        
        # Create enrollment and payment records
        with transaction.atomic():
            enrollment = Enrollment.objects.create(
                user=user,
                course=course,
                enrollment_type='individual',
                total_amount=course.total_price,
                tax_amount=course.tax_amount,
                payment_status='completed'
            )
            
            payment = Payment.objects.create(
                enrollment=enrollment,
                installment_number=1,
                amount=course.total_price,
                tax_amount=course.tax_amount,
                payment_method='razorpay',
                transaction_id=payment_id,
                payment_date=timezone.now(),
                due_date=timezone.now().date(),
                status='completed',
                notes=f'Razorpay Order ID: {order_id}',
                razorpay_order_id=order_id,
                razorpay_payment_id=payment_id,
                razorpay_signature=signature
            )
            
            # Create Tax Invoice for paid courses
            if course.total_price > 0:
                from apps.payments.models import TaxInvoice
                
                invoice_number = f"INV-{enrollment.id}-{payment.id}-{datetime.now().strftime('%Y%m%d')}"
                tax_invoice = TaxInvoice.objects.create(
                    enrollment=enrollment,
                    payment=payment,
                    invoice_number=invoice_number,
                    subtotal=course.price,  # Base price without tax
                    tax_rate=course.tax_rate * 100,  # Store as percentage
                    tax_amount=course.tax_amount,
                    total_amount=course.total_price
                )
                
                # Send enrollment confirmation email with invoice
                try:
                    from emails.invoice_generator import generate_invoice_pdf
                    from emails.utils import send_enrollment_confirmation_email
                    
                    # Generate PDF invoice
                    invoice_pdf_content = generate_invoice_pdf(tax_invoice)
                    
                    # Send enrollment confirmation email with invoice attachment
                    email_sent = send_enrollment_confirmation_email(
                        enrollment, 
                        include_invoice=True, 
                        invoice_pdf_content=invoice_pdf_content
                    )
                    
                    if email_sent:
                        print(f"Enrollment confirmation email sent to {user.email}")
                    else:
                        print(f"Failed to send enrollment confirmation email to {user.email}")
                        
                except Exception as email_error:
                    print(f"Error sending enrollment email: {str(email_error)}")
                    # Continue without failing the payment process
            else:
                # For free courses, still send enrollment confirmation without invoice
                try:
                    from emails.utils import send_enrollment_confirmation_email
                    email_sent = send_enrollment_confirmation_email(enrollment, include_invoice=False)
                    if email_sent:
                        print(f"Enrollment confirmation email sent to {user.email}")
                    else:
                        print(f"Failed to send enrollment confirmation email to {user.email}")
                except Exception as email_error:
                    print(f"Error sending enrollment email: {str(email_error)}")
        
        # For AJAX requests, return JSON
        if request.headers.get('Content-Type') == 'application/json':
            return JsonResponse({
                'status': 'success',
                'message': 'Payment successful! Enrollment completed.',
                'redirect_url': '/student/'  # Redirect to student portal
            })
        
        # For form submissions, redirect with success message
        messages.success(request, f'Payment successful! You are now enrolled in {course.title}.')
        print("=== PAYMENT SUCCESS COMPLETED ===")
        return redirect('student_portal:dashboard')
        
    except Exception as e:
        print(f"=== PAYMENT SUCCESS ERROR: {str(e)} ===")
        return JsonResponse({'status': 'error', 'message': f'Payment processing failed: {str(e)}'})

@csrf_exempt
@require_POST  
def payment_failed(request):
    """Handle failed payment callback from Razorpay"""
    try:
        error_data = json.loads(request.body)
        # Log the error for debugging
        print(f"Payment failed: {error_data}")
        
        return JsonResponse({
            'status': 'error',
            'message': 'Payment failed. Please try again.'
        })
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': 'Payment processing error'})

def contact(request):
    """Contact us page view"""
    return render(request, 'landing/contact.html')

def refund_policy(request):
    """Refund policy page view"""
    return render(request, 'landing/refund_policy.html')

def cancellation_policy(request):
    """Cancellation policy page view"""
    return render(request, 'landing/cancellation_policy.html')
