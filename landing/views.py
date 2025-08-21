import json
import razorpay
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib.auth import get_user_model
from django.contrib.auth.forms import UserCreationForm
from django.contrib import messages
from django.conf import settings
from django.db import transaction
from django.http import JsonResponse, HttpResponseBadRequest
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from django.utils import timezone
from django import forms

from apps.courses.models import Course
from apps.payments.models import Enrollment, Payment

User = get_user_model()

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
            user.phone = self.cleaned_data['phone']
        if commit:
            user.save()
        return user


def home(request):
    """Landing page view"""
    return render(request, 'landing/home.html')

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
        form = PublicUserRegistrationForm(request.POST)
        if form.is_valid():
            user = form.save()
            username = form.cleaned_data.get('username')
            
            # Send verification email
            from emails.utils import send_verification_email
            try:
                if send_verification_email(user):
                    messages.success(request, f'Account created for {username}! Please check your email to verify your account before logging in.')
                else:
                    messages.warning(request, f'Account created for {username}! However, there was an issue sending the verification email. You can still log in.')
            except Exception as e:
                messages.warning(request, f'Account created for {username}! There was an issue sending the verification email, but you can still log in.')
            
            return redirect('student_portal:login')
    else:
        form = PublicUserRegistrationForm()
    
    context = {
        'form': form,
    }
    return render(request, 'landing/register.html', context)


def courses(request):
    """Public courses listing page"""
    courses = Course.objects.filter(
        is_published=True, 
        allow_public_enrollment=True
    ).order_by('-created_at')
    
    context = {
        'courses': courses,
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
    if request.user.is_authenticated:
        is_enrolled = Enrollment.objects.filter(
            user=request.user, 
            course=course, 
            active=True
        ).exists()
    
    context = {
        'course': course,
        'is_enrolled': is_enrolled,
        'razorpay_key': getattr(settings, 'RAZORPAY_KEY_ID', ''),
    }
    return render(request, 'landing/course_detail.html', context)

@login_required
def enroll_course(request, course_id):
    """Handle course enrollment with payment"""
    course = get_object_or_404(
        Course, 
        id=course_id, 
        is_published=True, 
        allow_public_enrollment=True
    )
    
    # Security check: prevent duplicate enrollments
    if Enrollment.objects.filter(user=request.user, course=course, active=True).exists():
        messages.warning(request, 'You are already enrolled in this course.')
        return redirect('landing:course_detail', course_id=course.id)
    
    if request.method == 'POST':
        if course.is_free_course:
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
            # Paid course - create Razorpay order
            try:
                # Initialize Razorpay client
                client = razorpay.Client(auth=(
                    getattr(settings, 'RAZORPAY_KEY_ID', ''),
                    getattr(settings, 'RAZORPAY_KEY_SECRET', '')
                ))
                
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
                
                return render(request, 'landing/payment.html', context)
                
            except Exception as e:
                messages.error(request, f'Payment initialization failed: {str(e)}')
                return redirect('landing:course_detail', course_id=course.id)
    
    return redirect('landing:course_detail', course_id=course.id)

@csrf_exempt
@require_POST
def payment_success(request):
    """Handle successful payment callback from Razorpay"""
    try:
        # Get payment details from request
        payment_id = request.POST.get('razorpay_payment_id')
        order_id = request.POST.get('razorpay_order_id')
        signature = request.POST.get('razorpay_signature')
        
        if not all([payment_id, order_id, signature]):
            return HttpResponseBadRequest('Missing payment parameters')
        
        # Initialize Razorpay client
        client = razorpay.Client(auth=(
            getattr(settings, 'RAZORPAY_KEY_ID', ''),
            getattr(settings, 'RAZORPAY_KEY_SECRET', '')
        ))
        
        # Verify payment signature
        params_dict = {
            'razorpay_order_id': order_id,
            'razorpay_payment_id': payment_id,
            'razorpay_signature': signature
        }
        
        try:
            client.utility.verify_payment_signature(params_dict)
        except razorpay.errors.SignatureVerificationError:
            return JsonResponse({'status': 'error', 'message': 'Invalid payment signature'})
        
        # Fetch order details to get course and user info
        order_details = client.order.fetch(order_id)
        course_id = order_details['notes']['course_id']
        user_id = order_details['notes']['user_id']
        
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
                notes=f'Razorpay Order ID: {order_id}'
            )
        
        return JsonResponse({
            'status': 'success',
            'message': 'Payment successful! Enrollment completed.',
            'redirect_url': '/student/'  # Redirect to student portal
        })
        
    except Exception as e:
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
