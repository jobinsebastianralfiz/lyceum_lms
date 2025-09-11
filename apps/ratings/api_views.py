from rest_framework import generics, status, permissions
from rest_framework.response import Response
from rest_framework.decorators import api_view, permission_classes
from django.shortcuts import get_object_or_404
from django.db.models import Avg, Count, Q
from django.db import IntegrityError
from apps.courses.models import Course
from apps.payments.models import Enrollment
from apps.payments.services import EnrollmentService
from .models import CourseRating, CourseReview, ReviewHelpful
from .serializers import (
    CourseRatingSerializer, CourseRatingCreateSerializer,
    CourseReviewSerializer, CourseReviewCreateSerializer,
    RatingStatsSerializer
)


class CourseRatingListCreateView(generics.ListCreateAPIView):
    """
    List ratings for a course or create a new rating
    """
    permission_classes = [permissions.IsAuthenticated]
    
    def get_serializer_class(self):
        if self.request.method == 'POST':
            return CourseRatingCreateSerializer
        return CourseRatingSerializer
    
    def get_queryset(self):
        course_id = self.kwargs['course_id']
        return CourseRating.objects.filter(
            course_id=course_id, 
            is_approved=True
        ).select_related('user', 'course').order_by('-created_at')
    
    def perform_create(self, serializer):
        course_id = self.kwargs['course_id']
        course = get_object_or_404(Course, id=course_id)
        
        # Verify user can rate this course
        if not EnrollmentService.can_rate_course(self.request.user, course):
            from rest_framework.exceptions import PermissionDenied
            raise PermissionDenied("You must be enrolled in this course to rate it")
        
        # Check if user already has a rating for this course
        existing_rating = CourseRating.objects.filter(
            course=course, 
            user=self.request.user
        ).first()
        
        if existing_rating:
            # Update existing rating
            existing_rating.rating = serializer.validated_data['rating']
            existing_rating.review_text = serializer.validated_data.get('review_text', '')
            existing_rating.save()
            return existing_rating
        else:
            # Create new rating
            return serializer.save(user=self.request.user, course=course)
    
    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        try:
            rating = self.perform_create(serializer)
            response_serializer = CourseRatingSerializer(rating, context={'request': request})
            return Response(response_serializer.data, status=status.HTTP_201_CREATED)
        except IntegrityError:
            return Response(
                {'error': 'You have already rated this course'}, 
                status=status.HTTP_400_BAD_REQUEST
            )


class UserCourseRatingView(generics.RetrieveUpdateDestroyAPIView):
    """
    Get, update or delete a user's rating for a course
    """
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = CourseRatingSerializer
    
    def get_object(self):
        course_id = self.kwargs['course_id']
        return get_object_or_404(
            CourseRating, 
            course_id=course_id, 
            user=self.request.user
        )
    
    def update(self, request, *args, **kwargs):
        serializer = CourseRatingCreateSerializer(
            self.get_object(), 
            data=request.data, 
            partial=True,
            context={'request': request}
        )
        serializer.is_valid(raise_exception=True)
        rating = serializer.save()
        
        response_serializer = CourseRatingSerializer(rating, context={'request': request})
        return Response(response_serializer.data)


class CourseReviewListCreateView(generics.ListCreateAPIView):
    """
    List reviews for a course or create a new review
    """
    permission_classes = [permissions.IsAuthenticated]
    
    def get_serializer_class(self):
        if self.request.method == 'POST':
            return CourseReviewCreateSerializer
        return CourseReviewSerializer
    
    def get_queryset(self):
        course_id = self.kwargs['course_id']
        return CourseReview.objects.filter(
            course_id=course_id,
            is_approved=True
        ).select_related('user', 'rating', 'course').order_by('-created_at')
    
    def perform_create(self, serializer):
        course_id = self.kwargs['course_id']
        course = get_object_or_404(Course, id=course_id)
        
        # Verify user can rate this course
        if not EnrollmentService.can_rate_course(self.request.user, course):
            from rest_framework.exceptions import PermissionDenied
            raise PermissionDenied("You must be enrolled in this course to write reviews")
        
        # Get user's rating for this course
        user_rating = get_object_or_404(
            CourseRating,
            course=course,
            user=self.request.user
        )
        
        return serializer.save(
            user=self.request.user,
            course=course,
            rating=user_rating
        )
    
    def get_serializer_context(self):
        context = super().get_serializer_context()
        context['course_id'] = self.kwargs['course_id']
        return context


@api_view(['GET'])
@permission_classes([permissions.AllowAny])
def course_rating_stats(request, course_id):
    """
    Get rating statistics for a course
    """
    course = get_object_or_404(Course, id=course_id)
    ratings = CourseRating.objects.filter(course=course, is_approved=True)
    
    if not ratings.exists():
        return Response({
            'average_rating': 0.0,
            'total_ratings': 0,
            'rating_distribution': {str(i): 0 for i in range(1, 6)},
            'recent_ratings': []
        })
    
    # Calculate statistics
    avg_rating = ratings.aggregate(avg=Avg('rating'))['avg']
    total_ratings = ratings.count()
    
    # Rating distribution
    rating_distribution = {}
    for i in range(1, 6):
        count = ratings.filter(rating=i).count()
        rating_distribution[str(i)] = count
    
    # Recent ratings (last 5)
    recent_ratings = ratings.select_related('user')[:5]
    
    data = {
        'average_rating': round(float(avg_rating), 1) if avg_rating else 0.0,
        'total_ratings': total_ratings,
        'rating_distribution': rating_distribution,
        'recent_ratings': CourseRatingSerializer(recent_ratings, many=True, context={'request': request}).data
    }
    
    return Response(data)


@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def toggle_review_helpful(request, review_id):
    """
    Toggle helpful vote for a review
    """
    review = get_object_or_404(CourseReview, id=review_id, is_approved=True)
    
    # Check if user can rate/vote on this course using centralized service
    if not EnrollmentService.can_rate_course(request.user, review.course):
        return Response(
            {'error': 'You must be enrolled in this course to vote on reviews'}, 
            status=status.HTTP_403_FORBIDDEN
        )
    
    # Get or create helpful vote
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
    helpful_count = review.helpful_votes.filter(is_helpful=True).count()
    review.is_helpful_count = helpful_count
    review.save()
    
    return Response({
        'is_helpful': helpful_vote.is_helpful,
        'helpful_count': helpful_count
    })


@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def user_course_rating_status(request, course_id):
    """
    Check if user has rated/reviewed a course
    """
    course = get_object_or_404(Course, id=course_id)
    
    # Use centralized enrollment service that supports partial payments
    can_rate = EnrollmentService.can_rate_course(request.user, course)
    
    if not can_rate:
        return Response({
            'can_rate': False,
            'reason': 'You must be enrolled in this course to rate it'
        })
    
    # Check existing rating
    rating = CourseRating.objects.filter(course=course, user=request.user).first()
    review = CourseReview.objects.filter(course=course, user=request.user).first() if rating else None
    
    return Response({
        'can_rate': True,
        'has_rated': bool(rating),
        'has_reviewed': bool(review),
        'user_rating': CourseRatingSerializer(rating, context={'request': request}).data if rating else None,
        'user_review': CourseReviewSerializer(review, context={'request': request}).data if review else None
    })