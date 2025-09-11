# RATINGS & REVIEWS MANAGEMENT VIEWS

from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import user_passes_test
from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Q, Avg
from django.db import models
from apps.ratings.models import CourseRating, CourseReview, ReviewHelpful
from apps.courses.models import Course


def is_staff_user(user):
    return user.is_authenticated and user.is_staff


@user_passes_test(is_staff_user)
def ratings_list_view(request):
    """List all course ratings"""
    search_query = request.GET.get('search', '')
    course_filter = request.GET.get('course', '')
    rating_filter = request.GET.get('rating', '')
    status_filter = request.GET.get('status', '')
    
    ratings = CourseRating.objects.select_related('course', 'user').order_by('-created_at')
    
    # Apply filters
    if search_query:
        ratings = ratings.filter(
            Q(user__name__icontains=search_query) |
            Q(user__email__icontains=search_query) |
            Q(course__title__icontains=search_query) |
            Q(review_text__icontains=search_query)
        )
    
    if course_filter:
        ratings = ratings.filter(course_id=course_filter)
    
    if rating_filter:
        ratings = ratings.filter(rating=rating_filter)
    
    if status_filter:
        if status_filter == 'approved':
            ratings = ratings.filter(is_approved=True)
        elif status_filter == 'pending':
            ratings = ratings.filter(is_approved=False)
    
    # Pagination
    paginator = Paginator(ratings, 20)
    page_number = request.GET.get('page')
    ratings_page = paginator.get_page(page_number)
    
    # Get courses for filter dropdown
    courses = Course.objects.filter(is_published=True).order_by('title')
    
    # Statistics
    total_ratings = CourseRating.objects.count()
    approved_ratings = CourseRating.objects.filter(is_approved=True).count()
    pending_ratings = CourseRating.objects.filter(is_approved=False).count()
    
    context = {
        'ratings': ratings_page,
        'courses': courses,
        'search_query': search_query,
        'course_filter': course_filter,
        'rating_filter': rating_filter,
        'status_filter': status_filter,
        'total_ratings': total_ratings,
        'approved_ratings': approved_ratings,
        'pending_ratings': pending_ratings,
    }
    
    return render(request, 'custom_admin/ratings/ratings_list.html', context)

@user_passes_test(is_staff_user)
def rating_detail_view(request, rating_id):
    """View/edit single rating"""
    rating = get_object_or_404(CourseRating, id=rating_id)
    
    if request.method == 'POST':
        action = request.POST.get('action')
        
        if action == 'approve':
            rating.is_approved = True
            rating.save()
            messages.success(request, f'Rating approved successfully.')
        elif action == 'reject':
            rating.is_approved = False
            rating.save()
            messages.success(request, f'Rating rejected.')
        elif action == 'delete':
            course_title = rating.course.title
            rating.delete()
            messages.success(request, f'Rating for "{course_title}" deleted successfully.')
            return redirect('custom_admin:ratings_list')
    
    return render(request, 'custom_admin/ratings/detail.html', {'rating': rating})

@user_passes_test(is_staff_user)
def reviews_list_view(request):
    """List all course reviews"""
    search_query = request.GET.get('search', '')
    course_filter = request.GET.get('course', '')
    status_filter = request.GET.get('status', '')
    
    reviews = CourseReview.objects.select_related('course', 'user', 'rating').order_by('-created_at')
    
    # Apply filters
    if search_query:
        reviews = reviews.filter(
            Q(user__first_name__icontains=search_query) |
            Q(user__last_name__icontains=search_query) |
            Q(user__email__icontains=search_query) |
            Q(course__title__icontains=search_query) |
            Q(title__icontains=search_query) |
            Q(content__icontains=search_query)
        )
    
    if course_filter:
        reviews = reviews.filter(course_id=course_filter)
    
    if status_filter:
        if status_filter == 'approved':
            reviews = reviews.filter(is_approved=True)
        elif status_filter == 'pending':
            reviews = reviews.filter(is_approved__isnull=True)
        elif status_filter == 'rejected':
            reviews = reviews.filter(is_approved=False)
    
    # Pagination
    paginator = Paginator(reviews, 20)
    page_number = request.GET.get('page')
    reviews_page = paginator.get_page(page_number)
    
    # Get courses for filter dropdown
    courses = Course.objects.filter(is_published=True).order_by('title')
    
    # Statistics
    total_reviews = CourseReview.objects.count()
    approved_reviews = CourseReview.objects.filter(is_approved=True).count()
    pending_reviews = CourseReview.objects.filter(is_approved__isnull=True).count()
    rejected_reviews = CourseReview.objects.filter(is_approved=False).count()
    
    context = {
        'reviews': reviews_page,
        'courses': courses,
        'search_query': search_query,
        'course_filter': course_filter,
        'status_filter': status_filter,
        'total_reviews': total_reviews,
        'approved_reviews': approved_reviews,
        'pending_reviews': pending_reviews,
        'rejected_reviews': rejected_reviews,
    }
    
    return render(request, 'custom_admin/ratings/reviews_list.html', context)

@user_passes_test(is_staff_user)
def review_detail_view(request, review_id):
    """View/edit single review"""
    review = get_object_or_404(CourseReview, id=review_id)
    
    if request.method == 'POST':
        action = request.POST.get('action')
        
        if action == 'approve':
            review.is_approved = True
            review.save()
            messages.success(request, f'Review approved successfully.')
        elif action == 'reject':
            review.is_approved = False
            review.save()
            messages.success(request, f'Review rejected.')
        elif action == 'delete':
            course_title = review.course.title
            review.delete()
            messages.success(request, f'Review for "{course_title}" deleted successfully.')
            return redirect('custom_admin:reviews_list')
    
    # Get course statistics
    course = review.course
    course_stats = {
        'total_ratings': CourseRating.objects.filter(course=course).count(),
        'average_rating': CourseRating.objects.filter(course=course).aggregate(avg=Avg('rating'))['avg'] or 0,
        'total_reviews': CourseReview.objects.filter(course=course).count(),
        'approved_reviews': CourseReview.objects.filter(course=course, is_approved=True).count(),
    }
    
    context = {
        'review': review,
        'course_stats': course_stats,
    }
    
    return render(request, 'custom_admin/ratings/review_detail.html', context)

@user_passes_test(is_staff_user)
def review_votes_list_view(request):
    """List all review votes"""
    search_query = request.GET.get('search', '')
    
    votes = ReviewHelpful.objects.select_related('review__course', 'review__user', 'user').order_by('-created_at')
    
    # Apply filters
    if search_query:
        votes = votes.filter(
            Q(user__name__icontains=search_query) |
            Q(user__email__icontains=search_query) |
            Q(review__course__title__icontains=search_query) |
            Q(review__title__icontains=search_query)
        )
    
    # Pagination
    paginator = Paginator(votes, 20)
    page_number = request.GET.get('page')
    votes_page = paginator.get_page(page_number)
    
    # Statistics
    total_votes = ReviewHelpful.objects.count()
    helpful_votes = ReviewHelpful.objects.filter(is_helpful=True).count()
    not_helpful_votes = ReviewHelpful.objects.filter(is_helpful=False).count()
    
    context = {
        'votes': votes_page,
        'search_query': search_query,
        'total_votes': total_votes,
        'helpful_votes': helpful_votes,
        'not_helpful_votes': not_helpful_votes,
    }
    
    return render(request, 'custom_admin/ratings/review_votes_list.html', context)

@user_passes_test(is_staff_user, login_url='/admin/login/')
def rating_delete_view(request, rating_id):
    rating = get_object_or_404(CourseRating, id=rating_id)
    
    if request.method == 'POST':
        course_title = rating.course.title
        rating.delete()
        messages.success(request, f'Rating for "{course_title}" has been deleted successfully.')
        return redirect('custom_admin:ratings_list')
    
    context = {
        'rating': rating,
    }
    return render(request, 'custom_admin/ratings/rating_delete.html', context)

@user_passes_test(is_staff_user, login_url='/admin/login/')
def ratings_bulk_delete_view(request):
    if request.method == 'POST':
        rating_ids = request.POST.getlist('rating_ids')
        if rating_ids:
            deleted_count = CourseRating.objects.filter(id__in=rating_ids).delete()[0]
            messages.success(request, f'{deleted_count} ratings have been deleted successfully.')
        else:
            messages.warning(request, 'No ratings were selected for deletion.')
    
    return redirect('custom_admin:ratings_list')

@user_passes_test(is_staff_user, login_url='/admin/login/')
def review_approve_view(request, review_id):
    review = get_object_or_404(CourseReview, id=review_id)
    review.is_approved = True
    review.save()
    messages.success(request, f'Review by {review.user.first_name} has been approved.')
    return redirect('custom_admin:reviews_list')

@user_passes_test(is_staff_user, login_url='/admin/login/')
def review_reject_view(request, review_id):
    review = get_object_or_404(CourseReview, id=review_id)
    review.is_approved = False
    review.save()
    messages.warning(request, f'Review by {review.user.first_name} has been rejected.')
    return redirect('custom_admin:reviews_list')

@user_passes_test(is_staff_user, login_url='/admin/login/')
def review_delete_view(request, review_id):
    review = get_object_or_404(CourseReview, id=review_id)
    
    if request.method == 'POST':
        user_name = f"{review.user.first_name} {review.user.last_name}"
        review.delete()
        messages.success(request, f'Review by {user_name} has been deleted successfully.')
        return redirect('custom_admin:reviews_list')
    
    context = {
        'review': review,
    }
    return render(request, 'custom_admin/ratings/review_delete.html', context)

@user_passes_test(is_staff_user, login_url='/admin/login/')
def reviews_bulk_moderate_view(request):
    if request.method == 'POST':
        review_ids = request.POST.getlist('review_ids')
        action = request.POST.get('action')
        
        if review_ids:
            reviews = CourseReview.objects.filter(id__in=review_ids)
            
            if action == 'approve':
                reviews.update(is_approved=True)
                messages.success(request, f'{len(review_ids)} reviews have been approved successfully.')
            elif action == 'reject':
                reviews.update(is_approved=False)
                messages.warning(request, f'{len(review_ids)} reviews have been rejected.')
            elif action == 'delete':
                deleted_count = reviews.delete()[0]
                messages.success(request, f'{deleted_count} reviews have been deleted successfully.')
        else:
            messages.warning(request, 'No reviews were selected for moderation.')
    
    return redirect('custom_admin:reviews_list')