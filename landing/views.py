import json
import razorpay
import requests
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib.auth import get_user_model, authenticate, login
from django.contrib.auth.forms import UserCreationForm
from django.contrib import messages
from django.conf import settings
from django.db import transaction, models
from django.http import JsonResponse, HttpResponseBadRequest, HttpResponse
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
    """Landing page view with featured courses, dynamic banner, news and events"""
    from apps.content_management.models import News, Banner, Event, Testimonial, Placement, Achievement
    from django.utils import timezone

    courses = Course.objects.filter(
        is_published=True
    ).order_by('-created_at')[:6]  # Get featured courses (includes enquiry-only)

    # Get latest published news
    latest_news = News.objects.filter(
        is_published=True
    ).order_by('-published_at', '-created_at')[:3]

    # Get active HERO banners only (within date range, ordered by priority)
    now = timezone.now()
    hero_banners = Banner.objects.filter(
        is_active=True,
        banner_type='hero'  # Only hero type banners
    ).filter(
        # Check start_date: either null or in the past
        models.Q(start_date__isnull=True) | models.Q(start_date__lte=now)
    ).filter(
        # Check end_date: either null or in the future
        models.Q(end_date__isnull=True) | models.Q(end_date__gte=now)
    ).order_by('-priority', '-created_at')[:5]  # Max 5 banners

    # For backwards compatibility
    hero_banner = hero_banners.first() if hero_banners else None

    # Get upcoming events
    upcoming_events = Event.objects.filter(
        is_published=True,
        status='upcoming',
        event_date__gte=timezone.now().date()
    ).order_by('event_date', 'start_time')[:3]

    # Get featured testimonials
    featured_testimonials = Testimonial.objects.filter(
        is_published=True
    ).order_by('-is_featured', '-published_at')[:4]

    # Get featured placements
    featured_placements = Placement.objects.filter(
        is_published=True
    ).order_by('-is_featured', '-published_at')[:4]

    # Get featured achievements
    featured_achievements = Achievement.objects.filter(
        is_published=True
    ).order_by('-is_featured', '-achievement_date')[:4]

    context = {
        'courses': courses,
        'latest_news': latest_news,
        'hero_banners': hero_banners,
        'hero_banner': hero_banner,
        'upcoming_events': upcoming_events,
        'testimonials': featured_testimonials,
        'placements': featured_placements,
        'achievements': featured_achievements,
    }
    return render(request, 'landing/home.html', context)

def news_detail(request, slug):
    """News article detail page view"""
    from apps.content_management.models import News

    news = get_object_or_404(News, slug=slug, is_published=True)

    # Get related news (same category or recent news)
    related_news = News.objects.filter(
        is_published=True
    ).exclude(id=news.id).order_by('-published_at', '-created_at')[:3]

    context = {
        'news': news,
        'related_news': related_news,
    }
    return render(request, 'landing/news_detail.html', context)

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
        user_role = getattr(request.user, 'role', None)
        if request.user.is_staff or request.user.is_superuser:
            return redirect('custom_admin:dashboard')
        elif user_role == 'teacher':
            return redirect('teacher_portal:dashboard')
        elif user_role == 'admin':
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

            # Redirect based on user role/type
            user_role = getattr(user, 'role', None)

            if user.is_staff or user.is_superuser:
                messages.success(request, f'Welcome back, {user.get_full_name() or user.username}!')
                return redirect('custom_admin:dashboard')
            elif user_role == 'teacher':
                # Teachers go to teacher portal
                messages.success(request, f'Welcome back, {user.get_full_name() or user.username}!')
                return redirect('teacher_portal:dashboard')
            elif user_role == 'admin':
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
    """Public courses listing page with categories (includes enquiry-only courses)"""
    courses = Course.objects.filter(
        is_published=True
    ).select_related('category').order_by('-created_at')

    categories = Category.objects.filter(
        courses__is_published=True
    ).distinct().order_by('name')
    
    context = {
        'courses': courses,
        'categories': categories,
    }
    return render(request, 'landing/courses.html', context)

def course_detail(request, course_id):
    """Public course detail page for enrollment or enquiry"""
    course = get_object_or_404(
        Course,
        id=course_id,
        is_published=True
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
        'CLOUDFLARE_TURNSTILE_SITE_KEY': getattr(settings, 'CLOUDFLARE_TURNSTILE_SITE_KEY', ''),
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
            is_published=True
        )

        # Check enrollment type - only allow online_purchase courses
        if course.is_enquiry_only:
            messages.info(request, 'This course requires an enquiry. Please fill out the enquiry form to learn more.')
            return redirect('landing:course_detail', course_id=course.id)

        if course.is_admin_only:
            messages.info(request, 'This course requires admin enrollment. Please contact us for more information.')
            return redirect('landing:course_detail', course_id=course.id)

        if not course.can_purchase_online:
            messages.error(request, 'This course is not available for online enrollment.')
            return redirect('landing:course_detail', course_id=course.id)
        
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


# ============ NEWS VIEWS ============
def news_list(request):
    """News listing page with all published news"""
    from apps.content_management.models import News

    news_items = News.objects.filter(
        is_published=True
    ).order_by('-published_at', '-created_at')

    # Get categories for filtering
    categories = News.CATEGORY_CHOICES

    # Filter by category if provided
    category = request.GET.get('category')
    if category:
        news_items = news_items.filter(category=category)

    context = {
        'news_items': news_items,
        'categories': categories,
        'selected_category': category,
    }
    return render(request, 'landing/news_list.html', context)


# ============ EVENT VIEWS ============
def events_list(request):
    """Events listing page with upcoming and past events"""
    from apps.content_management.models import Event

    # Get upcoming events
    upcoming_events = Event.objects.filter(
        is_published=True,
        status='upcoming',
        event_date__gte=timezone.now().date()
    ).order_by('event_date', 'start_time')

    # Get past events
    past_events = Event.objects.filter(
        is_published=True,
        event_date__lt=timezone.now().date()
    ).order_by('-event_date')[:10]

    # Get event types for filtering
    event_types = Event.EVENT_TYPE_CHOICES

    # Filter by type if provided
    event_type = request.GET.get('type')
    if event_type:
        upcoming_events = upcoming_events.filter(event_type=event_type)
        past_events = past_events.filter(event_type=event_type)

    context = {
        'upcoming_events': upcoming_events,
        'past_events': past_events,
        'event_types': event_types,
        'selected_type': event_type,
    }
    return render(request, 'landing/events_list.html', context)


def event_detail(request, slug):
    """Event detail page"""
    from apps.content_management.models import Event

    event = get_object_or_404(Event, slug=slug, is_published=True)

    # Increment view count
    event.view_count += 1
    event.save(update_fields=['view_count'])

    # Get related events
    related_events = Event.objects.filter(
        is_published=True,
        event_type=event.event_type
    ).exclude(id=event.id).order_by('event_date')[:3]

    context = {
        'event': event,
        'related_events': related_events,
    }
    return render(request, 'landing/event_detail.html', context)


# ============ TESTIMONIAL VIEWS ============
def testimonials_list(request):
    """Testimonials listing page"""
    from apps.content_management.models import Testimonial

    testimonials = Testimonial.objects.filter(
        is_published=True
    ).order_by('-is_featured', '-published_at', '-created_at')

    # Filter by type if provided
    testimonial_type = request.GET.get('type')
    if testimonial_type:
        testimonials = testimonials.filter(testimonial_type=testimonial_type)

    context = {
        'testimonials': testimonials,
        'testimonial_types': Testimonial.TESTIMONIAL_TYPE_CHOICES,
        'selected_type': testimonial_type,
    }
    return render(request, 'landing/testimonials_list.html', context)


def testimonial_detail(request, pk):
    """Testimonial detail page"""
    from apps.content_management.models import Testimonial

    testimonial = get_object_or_404(Testimonial, pk=pk, is_published=True)

    # Get related testimonials
    related = Testimonial.objects.filter(
        is_published=True
    ).exclude(id=testimonial.id).order_by('-published_at')[:3]

    context = {
        'testimonial': testimonial,
        'related_testimonials': related,
    }
    return render(request, 'landing/testimonial_detail.html', context)


# ============ PLACEMENT VIEWS ============
def placements_list(request):
    """Placements listing page - success stories"""
    from apps.content_management.models import Placement

    placements = Placement.objects.filter(
        is_published=True
    ).order_by('-is_featured', '-published_at', '-created_at')

    # Filter by type if provided
    placement_type = request.GET.get('type')
    if placement_type:
        placements = placements.filter(placement_type=placement_type)

    context = {
        'placements': placements,
        'placement_types': Placement.PLACEMENT_TYPE_CHOICES,
        'selected_type': placement_type,
    }
    return render(request, 'landing/placements_list.html', context)


def placement_detail(request, pk):
    """Placement detail page - success story"""
    from apps.content_management.models import Placement

    placement = get_object_or_404(Placement, pk=pk, is_published=True)

    # Get related placements
    related = Placement.objects.filter(
        is_published=True
    ).exclude(id=placement.id).order_by('-published_at')[:3]

    context = {
        'placement': placement,
        'related_placements': related,
    }
    return render(request, 'landing/placement_detail.html', context)


# ============ ACHIEVEMENT VIEWS ============
def achievements_list(request):
    """Achievements listing page"""
    from apps.content_management.models import Achievement

    achievements = Achievement.objects.filter(
        is_published=True
    ).order_by('-is_featured', '-achievement_date')

    # Filter by type if provided
    achievement_type = request.GET.get('type')
    if achievement_type:
        achievements = achievements.filter(achievement_type=achievement_type)

    context = {
        'achievements': achievements,
        'achievement_types': Achievement.ACHIEVEMENT_TYPE_CHOICES,
        'selected_type': achievement_type,
    }
    return render(request, 'landing/achievements_list.html', context)


def achievement_detail(request, slug):
    """Achievement detail page"""
    from apps.content_management.models import Achievement

    achievement = get_object_or_404(Achievement, slug=slug, is_published=True)

    # Get related achievements
    related = Achievement.objects.filter(
        is_published=True
    ).exclude(id=achievement.id).order_by('-achievement_date')[:3]

    context = {
        'achievement': achievement,
        'related_achievements': related,
    }
    return render(request, 'landing/achievement_detail.html', context)


# ============ COURSE ENQUIRY ============
def course_enquiry(request, course_id):
    """Handle course enquiry form submission"""
    from apps.content_management.models import CourseEnquiry
    from django.contrib import messages
    from django.conf import settings
    import requests

    course = get_object_or_404(Course, id=course_id, is_published=True)

    if request.method != 'POST':
        messages.error(request, 'Invalid request method.')
        return redirect('landing:course_detail', course_id=course_id)

    # Verify Cloudflare Turnstile
    turnstile_token = request.POST.get('cf-turnstile-response', '')
    turnstile_secret = getattr(settings, 'CLOUDFLARE_TURNSTILE_SECRET_KEY', '')

    if turnstile_secret:  # Only verify if secret key is configured
        try:
            verify_response = requests.post(
                settings.CLOUDFLARE_TURNSTILE_VERIFY_URL,
                data={
                    'secret': turnstile_secret,
                    'response': turnstile_token,
                    'remoteip': request.META.get('REMOTE_ADDR', '')
                },
                timeout=10
            )
            result = verify_response.json()
            if not result.get('success', False):
                messages.error(request, 'Security verification failed. Please try again.')
                return redirect('landing:course_detail', course_id=course_id)
        except Exception as e:
            # Log error but don't block submission if Turnstile is down
            print(f"Turnstile verification error: {e}")

    # Get form data
    name = request.POST.get('name', '').strip()
    email = request.POST.get('email', '').strip()
    phone = request.POST.get('phone', '').strip()
    message_text = request.POST.get('message', '').strip()
    current_qualification = request.POST.get('current_qualification', '').strip()
    work_experience = request.POST.get('work_experience', '').strip()
    preferred_batch = request.POST.get('preferred_batch', '').strip()

    # Validate required fields
    if not name or not email or not phone:
        messages.error(request, 'Please fill in all required fields.')
        return redirect('landing:course_detail', course_id=course_id)

    # Get client IP
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0].strip()
    else:
        ip = request.META.get('REMOTE_ADDR')

    # Create the enquiry
    enquiry = CourseEnquiry.objects.create(
        course=course,
        name=name,
        email=email,
        phone=phone,
        message=message_text,
        current_qualification=current_qualification,
        work_experience=work_experience,
        preferred_batch=preferred_batch,
        source='website',
        user=request.user if request.user.is_authenticated else None,
        ip_address=ip,
        user_agent=request.META.get('HTTP_USER_AGENT', '')[:500],
        utm_source=request.GET.get('utm_source', ''),
        utm_medium=request.GET.get('utm_medium', ''),
        utm_campaign=request.GET.get('utm_campaign', ''),
    )

    messages.success(
        request,
        f'Thank you for your enquiry about "{course.title}"! Our team will contact you within 24 hours.'
    )
    return redirect('landing:course_detail', course_id=course_id)


def robots_txt(request):
    """Serve robots.txt for SEO."""
    content = """User-agent: *
Allow: /
Disallow: /admin/
Disallow: /api/
Disallow: /student/
Disallow: /teacher/
Disallow: /django-admin/

Sitemap: https://www.lmacademy.info/sitemap.xml
"""
    return HttpResponse(content, content_type='text/plain')
