from django.shortcuts import render

def home(request):
    """Landing page view"""
    return render(request, 'landing/home.html')

def privacy_policy(request):
    """Privacy policy page view"""
    return render(request, 'landing/privacy_policy.html')

def terms_conditions(request):
    """Terms and conditions page view"""
    return render(request, 'landing/terms_conditions.html')
