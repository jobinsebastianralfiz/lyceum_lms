from rest_framework import serializers
from drf_spectacular.utils import extend_schema_field
from .models import CourseRating, CourseReview, ReviewHelpful


class CourseRatingSerializer(serializers.ModelSerializer):
    """
    Serializer for course ratings
    """
    user_name = serializers.CharField(source='user.name', read_only=True)
    user_username = serializers.CharField(source='user.username', read_only=True)
    star_display = serializers.CharField(read_only=True)
    
    class Meta:
        model = CourseRating
        fields = [
            'id', 'course', 'rating', 'review_text', 'created_at', 
            'updated_at', 'user_name', 'user_username', 'star_display'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at', 'user_name', 'user_username', 'star_display']


class CourseRatingCreateSerializer(serializers.ModelSerializer):
    """
    Serializer for creating/updating course ratings
    """
    class Meta:
        model = CourseRating
        fields = ['course', 'rating', 'review_text']
    
    def validate_rating(self, value):
        if value < 1 or value > 5:
            raise serializers.ValidationError("Rating must be between 1 and 5 stars")
        return value
    
    def validate_course(self, value):
        request = self.context.get('request')
        if not request or not request.user.is_authenticated:
            raise serializers.ValidationError("You must be logged in to rate a course")
        
        # Check if user can rate this course using centralized service
        from apps.payments.services import EnrollmentService
        
        if not EnrollmentService.can_rate_course(request.user, value):
            raise serializers.ValidationError("You must be enrolled in this course to rate it")
        
        return value


class CourseReviewSerializer(serializers.ModelSerializer):
    """
    Serializer for course reviews
    """
    user_name = serializers.CharField(source='user.name', read_only=True)
    user_username = serializers.CharField(source='user.username', read_only=True)
    rating_value = serializers.IntegerField(source='rating.rating', read_only=True)
    helpful_count = serializers.SerializerMethodField()
    is_helpful_by_user = serializers.SerializerMethodField()
    
    class Meta:
        model = CourseReview
        fields = [
            'id', 'title', 'content', 'created_at', 'updated_at', 
            'user_name', 'user_username', 'rating_value', 'helpful_count',
            'is_helpful_by_user'
        ]
        read_only_fields = [
            'id', 'created_at', 'updated_at', 'user_name', 'user_username', 
            'rating_value', 'helpful_count', 'is_helpful_by_user'
        ]
    
    @extend_schema_field(serializers.IntegerField)
    def get_helpful_count(self, obj):
        return obj.helpful_votes.filter(is_helpful=True).count()
    
    @extend_schema_field(serializers.BooleanField)
    def get_is_helpful_by_user(self, obj):
        request = self.context.get('request')
        if not request or not request.user.is_authenticated:
            return False
        
        vote = obj.helpful_votes.filter(user=request.user).first()
        return vote.is_helpful if vote else False


class CourseReviewCreateSerializer(serializers.ModelSerializer):
    """
    Serializer for creating course reviews
    """
    class Meta:
        model = CourseReview
        fields = ['title', 'content']
    
    def validate(self, data):
        request = self.context.get('request')
        course_id = self.context.get('course_id')
        
        if not request or not request.user.is_authenticated:
            raise serializers.ValidationError("You must be logged in to write a review")
        
        if not course_id:
            raise serializers.ValidationError("Course ID is required")
        
        # Check if user has a rating for this course
        user_rating = CourseRating.objects.filter(
            course_id=course_id, 
            user=request.user
        ).first()
        
        if not user_rating:
            raise serializers.ValidationError("Please rate the course first before writing a review")
        
        return data


class RatingStatsSerializer(serializers.Serializer):
    """
    Serializer for rating statistics
    """
    average_rating = serializers.FloatField()
    total_ratings = serializers.IntegerField()
    rating_distribution = serializers.DictField()
    recent_ratings = CourseRatingSerializer(many=True, read_only=True)