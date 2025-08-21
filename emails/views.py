from django.shortcuts import render, redirect
from django.contrib import messages
from django.http import HttpResponse
from django.views.decorators.http import require_http_methods
from .utils import verify_email_token


def verify_email(request, token):
    """Verify email with token"""
    success, message = verify_email_token(token)
    
    if success:
        messages.success(request, message)
        # Redirect to login page after successful verification
        return redirect('student_portal:login')
    else:
        messages.error(request, message)
        return redirect('landing:register')


@require_http_methods(["GET"])
def verification_status(request):
    """Simple page showing verification status"""
    return render(request, 'emails/verification_status.html')
