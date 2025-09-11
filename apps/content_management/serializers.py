from rest_framework import serializers
from django.utils import timezone
from .models import Lead, News, Placement, Testimonial, LeadFollowUp


class LeadCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating new leads from mobile app"""
    
    class Meta:
        model = Lead
        fields = [
            'name', 'email', 'phone', 'area_of_interest', 'other_interest',
            'current_experience', 'career_goals', 'learning_timeline', 
            'budget_range', 'preferred_time', 'specific_topics'
        ]
        
    def validate_email(self, value):
        """Check if lead with this email already exists recently and is still pending"""
        from datetime import timedelta
        
        # Get the current request user if available
        request = self.context.get('request')
        current_user = request.user if request and request.user.is_authenticated else None
        
        # Define statuses that allow new lead submission
        completed_statuses = ['completed', 'converted', 'not_interested']
        
        # Check for recent leads
        recent_leads_query = Lead.objects.filter(
            created_at__gte=timezone.now() - timedelta(days=30)
        )
        
        if current_user:
            # If user is authenticated, check by user first
            user_recent_lead = recent_leads_query.filter(submitted_by=current_user).first()
            if user_recent_lead and user_recent_lead.is_active:
                raise serializers.ValidationError(
                    f"You have a pending lead application. Current status: {user_recent_lead.get_status_display()}. "
                    "Our team will contact you soon. You can submit a new application once the current one is completed."
                )
        else:
            # If user is anonymous, check by email
            email_recent_lead = recent_leads_query.filter(email=value).first()
            if email_recent_lead and email_recent_lead.is_active:
                raise serializers.ValidationError(
                    f"A lead with this email was already submitted recently. Current status: {email_recent_lead.get_status_display()}. "
                    "Our team will contact you soon. You can submit a new application once the current one is completed."
                )
        
        return value


class LeadListSerializer(serializers.ModelSerializer):
    """Serializer for listing leads in admin"""
    assigned_to_name = serializers.CharField(source='assigned_to.name', read_only=True)
    follow_up_count = serializers.SerializerMethodField()
    
    class Meta:
        model = Lead
        fields = [
            'id', 'name', 'email', 'phone', 'area_of_interest', 'current_experience',
            'status', 'assigned_to_name', 'follow_up_count', 'created_at'
        ]
    
    def get_follow_up_count(self, obj):
        return obj.follow_ups.count()


class LeadDetailSerializer(serializers.ModelSerializer):
    """Detailed serializer for individual lead management"""
    assigned_to_name = serializers.CharField(source='assigned_to.name', read_only=True)
    follow_ups = serializers.SerializerMethodField()
    
    class Meta:
        model = Lead
        fields = '__all__'
        
    def get_follow_ups(self, obj):
        return LeadFollowUpSerializer(obj.follow_ups.all()[:5], many=True).data


class LeadFollowUpSerializer(serializers.ModelSerializer):
    """Serializer for lead follow-up activities"""
    created_by_name = serializers.CharField(source='created_by.name', read_only=True)
    
    class Meta:
        model = LeadFollowUp
        fields = '__all__'
        read_only_fields = ['created_by']


class StudentLeadStatusSerializer(serializers.ModelSerializer):
    """Serializer for students to view their lead status"""
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    area_of_interest_display = serializers.CharField(source='get_area_of_interest_display', read_only=True)
    assigned_to_name = serializers.CharField(source='assigned_to.name', read_only=True)
    is_active = serializers.BooleanField(read_only=True)
    can_submit_new = serializers.BooleanField(source='allows_new_submission', read_only=True)
    
    class Meta:
        model = Lead
        fields = [
            'id', 'name', 'email', 'phone', 'area_of_interest', 'area_of_interest_display',
            'other_interest', 'current_experience', 'career_goals', 'learning_timeline',
            'budget_range', 'preferred_time', 'specific_topics', 'status', 'status_display',
            'assigned_to_name', 'is_active', 'can_submit_new', 'created_at', 'updated_at'
        ]
        read_only_fields = ['__all__']


class StudentLeadListSerializer(serializers.ModelSerializer):
    """Minimal serializer for listing student's leads"""
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    area_of_interest_display = serializers.CharField(source='get_area_of_interest_display', read_only=True)
    is_active = serializers.BooleanField(read_only=True)
    can_submit_new = serializers.BooleanField(source='allows_new_submission', read_only=True)
    
    class Meta:
        model = Lead
        fields = [
            'id', 'area_of_interest', 'area_of_interest_display', 'status', 
            'status_display', 'is_active', 'can_submit_new', 'created_at', 'updated_at'
        ]
        read_only_fields = ['__all__']


class NewsListSerializer(serializers.ModelSerializer):
    """Serializer for listing news in mobile app"""
    created_by_name = serializers.CharField(source='created_by.name', read_only=True)
    
    class Meta:
        model = News
        fields = [
            'id', 'title', 'slug', 'excerpt', 'featured_image', 'thumbnail',
            'category', 'is_featured', 'published_at', 'created_by_name', 'view_count'
        ]


class NewsDetailSerializer(serializers.ModelSerializer):
    """Detailed serializer for news articles"""
    created_by_name = serializers.CharField(source='created_by.name', read_only=True)
    tags_list = serializers.SerializerMethodField()
    
    class Meta:
        model = News
        fields = [
            'id', 'title', 'slug', 'content', 'excerpt', 'featured_image',
            'category', 'tags_list', 'published_at', 'created_by_name', 'view_count'
        ]
    
    def get_tags_list(self, obj):
        if obj.tags:
            return [tag.strip() for tag in obj.tags.split(',')]
        return []


class NewsCreateUpdateSerializer(serializers.ModelSerializer):
    """Serializer for creating/updating news articles"""
    
    class Meta:
        model = News
        fields = [
            'title', 'content', 'excerpt', 'featured_image', 'thumbnail',
            'category', 'tags', 'meta_title', 'meta_description', 
            'is_published', 'is_featured'
        ]
        
    def create(self, validated_data):
        if validated_data.get('is_published') and not validated_data.get('published_at'):
            validated_data['published_at'] = timezone.now()
        return super().create(validated_data)


class PlacementListSerializer(serializers.ModelSerializer):
    """Serializer for listing placements"""
    package_display = serializers.SerializerMethodField()
    
    class Meta:
        model = Placement
        fields = [
            'id', 'student_name', 'student_photo', 'course_completed',
            'company_name', 'company_logo', 'job_title', 'placement_type',
            'package_display', 'location', 'published_at', 'is_featured'
        ]
    
    def get_package_display(self, obj):
        if obj.can_show_package:
            return f"{obj.package_currency} {obj.package_amount:,.0f}"
        return "Package not disclosed"


class PlacementDetailSerializer(serializers.ModelSerializer):
    """Detailed serializer for placement stories"""
    package_display = serializers.SerializerMethodField()
    created_by_name = serializers.CharField(source='created_by.name', read_only=True)
    
    class Meta:
        model = Placement
        exclude = ['created_by']
        
    def get_package_display(self, obj):
        if obj.can_show_package:
            return f"{obj.package_currency} {obj.package_amount:,.0f}"
        return "Package not disclosed"


class PlacementCreateUpdateSerializer(serializers.ModelSerializer):
    """Serializer for creating/updating placements"""
    
    class Meta:
        model = Placement
        fields = [
            'student_name', 'student_photo', 'course_completed', 'batch_year',
            'company_name', 'company_logo', 'job_title', 'placement_type',
            'package_amount', 'package_currency', 'location', 'success_story',
            'key_achievements', 'skills_gained', 'technologies_used',
            'is_published', 'is_featured', 'consent_given', 'can_show_package'
        ]
        
    def create(self, validated_data):
        if validated_data.get('is_published') and not validated_data.get('published_at'):
            validated_data['published_at'] = timezone.now()
        return super().create(validated_data)


class TestimonialListSerializer(serializers.ModelSerializer):
    """Serializer for listing testimonials"""
    youtube_thumbnail_url = serializers.ReadOnlyField()
    
    class Meta:
        model = Testimonial
        fields = [
            'id', 'student_name', 'student_photo', 'course_name', 'batch_year',
            'testimonial_type', 'testimonial_text', 'youtube_video_id', 'youtube_thumbnail_url',
            'video_thumbnail', 'overall_rating', 'current_position', 'current_company',
            'is_featured', 'published_at', 'likes_count'
        ]


class TestimonialDetailSerializer(serializers.ModelSerializer):
    """Detailed serializer for testimonials"""
    youtube_thumbnail_url = serializers.ReadOnlyField()
    youtube_embed_url = serializers.ReadOnlyField()
    created_by_name = serializers.CharField(source='created_by.name', read_only=True)
    
    class Meta:
        model = Testimonial
        exclude = ['created_by']


class TestimonialCreateUpdateSerializer(serializers.ModelSerializer):
    """Serializer for creating/updating testimonials"""
    
    class Meta:
        model = Testimonial
        fields = [
            'student_name', 'student_photo', 'course_name', 'batch_year',
            'testimonial_type', 'testimonial_text', 'youtube_url', 'uploaded_video',
            'video_thumbnail', 'audio_file', 'overall_rating', 'course_rating',
            'instructor_rating', 'key_learnings', 'career_impact', 'recommendation',
            'current_position', 'current_company', 'is_published', 'is_featured',
            'consent_given', 'can_show_details'
        ]
        
    def validate(self, data):
        testimonial_type = data.get('testimonial_type')
        
        if testimonial_type == 'video_youtube':
            if not data.get('youtube_url'):
                raise serializers.ValidationError({
                    'youtube_url': 'YouTube URL is required for video testimonials.'
                })
        elif testimonial_type == 'text_image':
            if not data.get('testimonial_text'):
                raise serializers.ValidationError({
                    'testimonial_text': 'Text content is required for text testimonials.'
                })
        elif testimonial_type == 'video_upload':
            if not data.get('uploaded_video'):
                raise serializers.ValidationError({
                    'uploaded_video': 'Video file is required for uploaded video testimonials.'
                })
        elif testimonial_type == 'audio':
            if not data.get('audio_file'):
                raise serializers.ValidationError({
                    'audio_file': 'Audio file is required for audio testimonials.'
                })
                
        return data
    
    def create(self, validated_data):
        if validated_data.get('is_published') and not validated_data.get('published_at'):
            validated_data['published_at'] = timezone.now()
        return super().create(validated_data)


# Simplified serializers for mobile app responses
class NewsSimpleSerializer(serializers.ModelSerializer):
    """Minimal news data for mobile app"""
    class Meta:
        model = News
        fields = ['id', 'title', 'excerpt', 'thumbnail', 'category', 'published_at']


class PlacementSimpleSerializer(serializers.ModelSerializer):
    """Minimal placement data for mobile app"""
    package_display = serializers.SerializerMethodField()
    
    class Meta:
        model = Placement
        fields = ['id', 'student_name', 'company_name', 'job_title', 'package_display']
        
    def get_package_display(self, obj):
        if obj.can_show_package:
            return f"{obj.package_currency} {obj.package_amount:,.0f}"
        return "Package disclosed"


class TestimonialSimpleSerializer(serializers.ModelSerializer):
    """Minimal testimonial data for mobile app"""
    class Meta:
        model = Testimonial
        fields = ['id', 'student_name', 'course_name', 'overall_rating', 'testimonial_type']


# Dashboard/Statistics serializers
class ContentStatsSerializer(serializers.Serializer):
    """Statistics for admin dashboard"""
    total_leads = serializers.IntegerField()
    new_leads = serializers.IntegerField()
    leads_this_month = serializers.IntegerField()
    total_news = serializers.IntegerField()
    published_news = serializers.IntegerField()
    total_placements = serializers.IntegerField()
    total_testimonials = serializers.IntegerField()
    featured_content = serializers.IntegerField()