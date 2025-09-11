from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.db.models import Avg, Count, Q
from django.core.paginator import Paginator
from apps.courses.models import Course
from apps.payments.models import Enrollment
from apps.payments.services import EnrollmentService
from .models import CourseRating, CourseReview, ReviewHelpful
from .forms import CourseRatingForm, CourseReviewForm, RatingFilterForm


@login_required
def add_rating(request, course_id):
    try:
        course = get_object_or_404(Course, id=course_id)
    except:
        messages.error(request, "Course not found.")
        return redirect('student_portal:my_courses')
    
    # Determine if request is from student portal
    referer = request.META.get('HTTP_REFERER', '')
    is_student_portal = '/student/' in referer or 'student' in request.GET.get('source', '')
    
    # Check if user can rate this course (includes partial payments)
    can_rate = EnrollmentService.can_rate_course(request.user, course)
    enrollment = EnrollmentService.get_user_enrollment(request.user, course) or \
                 Enrollment.objects.filter(user=request.user, course=course, active=True, payment_status='partial').first()
    
    if not can_rate:
        messages.error(request, "You must be enrolled in this course to leave a rating.")
        try:
            if is_student_portal:
                return redirect('student_portal:course_detail', course_id=course.id)
            return redirect('landing:course_detail', course_id=course.id)
        except:
            return redirect('student_portal:my_courses')
    
    # Check if user has already rated this course
    existing_rating = CourseRating.objects.filter(course=course, user=request.user).first()
    
    if request.method == 'POST':
        form = CourseRatingForm(request.POST, instance=existing_rating)
        if form.is_valid():
            rating = form.save(commit=False)
            rating.course = course
            rating.user = request.user
            rating.save()
            
            action = "updated" if existing_rating else "added"
            messages.success(request, f"Your rating has been {action} successfully!")
            try:
                if is_student_portal:
                    return redirect('student_portal:course_detail', course_id=course.id)
                return redirect('landing:course_detail', course_id=course.id)
            except:
                return redirect('student_portal:my_courses')
    else:
        form = CourseRatingForm(instance=existing_rating)
    
    context = {
        'course': course,
        'form': form,
        'existing_rating': existing_rating,
        'enrollment': enrollment
    }
    
    # Use student portal template if request came from student portal
    template = 'ratings/add_rating_student.html' if is_student_portal else 'ratings/add_rating.html'
    return render(request, template, context)


@login_required
def add_review(request, course_id):
    course = get_object_or_404(Course, id=course_id)
    
    # Determine if request is from student portal
    referer = request.META.get('HTTP_REFERER', '')
    is_student_portal = '/student/' in referer or 'student' in request.GET.get('source', '')
    
    # Check if user can rate this course (includes partial payments)
    can_rate = EnrollmentService.can_rate_course(request.user, course)
    enrollment = EnrollmentService.get_user_enrollment(request.user, course) or \
                 Enrollment.objects.filter(user=request.user, course=course, active=True, payment_status='partial').first()
    
    if not can_rate:
        messages.error(request, "You must be enrolled in this course to write a review.")
        if is_student_portal:
            return redirect('student_portal:course_detail', course_id=course.id)
        return redirect('landing:course_detail', course_id=course.id)
    
    # Check if user has a rating for this course
    user_rating = CourseRating.objects.filter(course=course, user=request.user).first()
    if not user_rating:
        messages.error(request, "Please rate the course first before writing a detailed review.")
        return redirect('ratings:add_rating', course_id=course.id)
    
    # Check if user has already written a review
    existing_review = CourseReview.objects.filter(rating=user_rating).first()
    
    if request.method == 'POST':
        form = CourseReviewForm(request.POST, instance=existing_review)
        if form.is_valid():
            review = form.save(commit=False)
            review.course = course
            review.user = request.user
            review.rating = user_rating
            review.save()
            
            action = "updated" if existing_review else "added"
            messages.success(request, f"Your review has been {action} successfully!")
            if is_student_portal:
                return redirect('student_portal:course_detail', course_id=course.id)
            return redirect('landing:course_detail', course_id=course.id)
    else:
        form = CourseReviewForm(instance=existing_review)
    
    context = {
        'course': course,
        'form': form,
        'user_rating': user_rating,
        'existing_review': existing_review,
        'enrollment': enrollment
    }
    
    # Use student portal template if request came from student portal
    template = 'ratings/add_review_student.html' if is_student_portal else 'ratings/add_review.html'
    return render(request, template, context)


def course_reviews(request, course_id):
    course = get_object_or_404(Course, id=course_id)
    filter_form = RatingFilterForm(request.GET)
    
    # Base queryset
    ratings = CourseRating.objects.filter(
        course=course, 
        is_approved=True
    ).select_related('user')
    
    reviews = CourseReview.objects.filter(
        course=course, 
        is_approved=True
    ).select_related('user', 'rating')
    
    # Apply filters
    if filter_form.is_valid():
        rating_filter = filter_form.cleaned_data.get('rating_filter')
        sort_by = filter_form.cleaned_data.get('sort_by')
        
        if rating_filter and rating_filter != 'all':
            ratings = ratings.filter(rating=int(rating_filter))
            reviews = reviews.filter(rating__rating=int(rating_filter))
        
        # Apply sorting
        if sort_by == 'oldest':
            ratings = ratings.order_by('created_at')
            reviews = reviews.order_by('created_at')
        elif sort_by == 'highest_rating':
            ratings = ratings.order_by('-rating', '-created_at')
            reviews = reviews.order_by('-rating__rating', '-created_at')
        elif sort_by == 'lowest_rating':
            ratings = ratings.order_by('rating', '-created_at')
            reviews = reviews.order_by('rating__rating', '-created_at')
        elif sort_by == 'most_helpful':
            reviews = reviews.order_by('-is_helpful_count', '-created_at')
        else:  # newest (default)
            ratings = ratings.order_by('-created_at')
            reviews = reviews.order_by('-created_at')
    
    # Pagination
    ratings_paginator = Paginator(ratings, 10)
    reviews_paginator = Paginator(reviews, 5)
    
    ratings_page = request.GET.get('ratings_page', 1)
    reviews_page = request.GET.get('reviews_page', 1)
    
    ratings_obj = ratings_paginator.get_page(ratings_page)
    reviews_obj = reviews_paginator.get_page(reviews_page)
    
    # Rating statistics
    rating_stats = CourseRating.objects.filter(
        course=course, 
        is_approved=True
    ).aggregate(
        avg_rating=Avg('rating'),
        total_ratings=Count('id'),
        five_star=Count('id', filter=Q(rating=5)),
        four_star=Count('id', filter=Q(rating=4)),
        three_star=Count('id', filter=Q(rating=3)),
        two_star=Count('id', filter=Q(rating=2)),
        one_star=Count('id', filter=Q(rating=1)),
    )
    
    # Check if current user can rate/review
    user_can_rate = False
    user_rating = None
    user_review = None
    
    if request.user.is_authenticated:
        user_can_rate = EnrollmentService.can_rate_course(request.user, course)
        user_rating = CourseRating.objects.filter(course=course, user=request.user).first()
        if user_rating:
            user_review = CourseReview.objects.filter(rating=user_rating).first()
    
    context = {
        'course': course,
        'ratings': ratings_obj,
        'reviews': reviews_obj,
        'rating_stats': rating_stats,
        'filter_form': filter_form,
        'user_can_rate': user_can_rate,
        'user_rating': user_rating,
        'user_review': user_review,
    }
    return render(request, 'ratings/course_reviews.html', context)


@login_required
def toggle_helpful(request, review_id):
    if request.method == 'POST':
        review = get_object_or_404(CourseReview, id=review_id)
        
        # Check if user can rate/vote on this course using centralized service
        if not EnrollmentService.can_rate_course(request.user, review.course):
            return JsonResponse({'success': False, 'error': 'You must be enrolled to vote.'})
        
        helpful_vote, created = ReviewHelpful.objects.get_or_create(
            review=review,
            user=request.user,
            defaults={'is_helpful': True}
        )
        
        if not created:
            # Toggle the vote
            helpful_vote.is_helpful = not helpful_vote.is_helpful
            helpful_vote.save()
        
        # Update helpful count
        review.is_helpful_count = review.helpful_votes.filter(is_helpful=True).count()
        review.save()
        
        return JsonResponse({
            'success': True,
            'is_helpful': helpful_vote.is_helpful,
            'helpful_count': review.is_helpful_count
        })
    
    return JsonResponse({'success': False, 'error': 'Invalid request method.'})