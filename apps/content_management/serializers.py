from rest_framework import serializers
from django.utils import timezone
from .models import Lead, News, Placement, Testimonial, LeadFollowUp, Event, Achievement, Banner, CourseEnquiry


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


# ==================== EVENT SERIALIZERS ====================

class EventListSerializer(serializers.ModelSerializer):
    """Serializer for listing events in mobile app"""
    event_type_display = serializers.CharField(source='get_event_type_display', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    is_upcoming = serializers.BooleanField(read_only=True)
    days_until_event = serializers.SerializerMethodField()
    featured_image_url = serializers.SerializerMethodField()

    class Meta:
        model = Event
        fields = [
            'id', 'title', 'slug', 'short_description', 'event_type', 'event_type_display',
            'featured_image', 'featured_image_url', 'event_date', 'start_time', 'end_time',
            'timezone', 'is_online', 'venue_name', 'venue_address',
            'registration_required', 'max_attendees',
            'is_featured', 'status', 'status_display', 'is_upcoming',
            'days_until_event', 'published_at'
        ]

    def get_days_until_event(self, obj):
        if hasattr(obj, 'is_upcoming') and obj.is_upcoming:
            delta = obj.event_date - timezone.now().date()
            return delta.days
        return None

    def get_featured_image_url(self, obj):
        if obj.featured_image:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.featured_image.url)
            return obj.featured_image.url
        return None


class EventDetailSerializer(serializers.ModelSerializer):
    """Detailed serializer for event pages"""
    event_type_display = serializers.CharField(source='get_event_type_display', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    is_upcoming = serializers.BooleanField(read_only=True)
    featured_image_url = serializers.SerializerMethodField()
    thumbnail_url = serializers.SerializerMethodField()
    created_by_name = serializers.SerializerMethodField()

    class Meta:
        model = Event
        exclude = ['created_by', 'meeting_password']

    def get_featured_image_url(self, obj):
        if obj.featured_image:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.featured_image.url)
            return obj.featured_image.url
        return None

    def get_thumbnail_url(self, obj):
        if obj.thumbnail:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.thumbnail.url)
            return obj.thumbnail.url
        return None

    def get_created_by_name(self, obj):
        if obj.created_by:
            return obj.created_by.name if hasattr(obj.created_by, 'name') else obj.created_by.username
        return None


class EventSimpleSerializer(serializers.ModelSerializer):
    """Minimal event data for dashboard/cards"""
    event_type_display = serializers.CharField(source='get_event_type_display', read_only=True)

    class Meta:
        model = Event
        fields = ['id', 'title', 'event_type', 'event_type_display', 'event_date', 'start_time', 'is_online']


# ==================== ACHIEVEMENT SERIALIZERS ====================

class AchievementListSerializer(serializers.ModelSerializer):
    """Serializer for listing achievements"""
    achievement_type_display = serializers.CharField(source='get_achievement_type_display', read_only=True)
    badge_icon_url = serializers.SerializerMethodField()
    image_url = serializers.SerializerMethodField()

    class Meta:
        model = Achievement
        fields = [
            'id', 'title', 'slug', 'short_description', 'achievement_type', 'achievement_type_display',
            'badge_icon', 'badge_icon_url', 'image', 'image_url', 'awarded_by',
            'achievement_date', 'year', 'category', 'is_featured'
        ]

    def get_badge_icon_url(self, obj):
        if obj.badge_icon:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.badge_icon.url)
            return obj.badge_icon.url
        return None

    def get_image_url(self, obj):
        if obj.image:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.image.url)
            return obj.image.url
        return None


class AchievementDetailSerializer(serializers.ModelSerializer):
    """Detailed serializer for achievements"""
    achievement_type_display = serializers.CharField(source='get_achievement_type_display', read_only=True)
    badge_icon_url = serializers.SerializerMethodField()
    image_url = serializers.SerializerMethodField()
    certificate_url = serializers.SerializerMethodField()
    created_by_name = serializers.SerializerMethodField()

    class Meta:
        model = Achievement
        exclude = ['created_by']

    def get_badge_icon_url(self, obj):
        if obj.badge_icon:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.badge_icon.url)
            return obj.badge_icon.url
        return None

    def get_image_url(self, obj):
        if obj.image:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.image.url)
            return obj.image.url
        return None

    def get_certificate_url(self, obj):
        if obj.certificate:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.certificate.url)
            return obj.certificate.url
        return None

    def get_created_by_name(self, obj):
        if obj.created_by:
            return obj.created_by.name if hasattr(obj.created_by, 'name') else obj.created_by.username
        return None


class AchievementSimpleSerializer(serializers.ModelSerializer):
    """Minimal achievement data for dashboard stats"""
    class Meta:
        model = Achievement
        fields = ['id', 'title', 'year', 'badge_icon', 'awarded_by']


# ==================== BANNER SERIALIZERS ====================

class BannerSerializer(serializers.ModelSerializer):
    """Serializer for banners/hero sections"""
    banner_type_display = serializers.CharField(source='get_banner_type_display', read_only=True)
    is_currently_active = serializers.SerializerMethodField()
    background_image_url = serializers.SerializerMethodField()
    featured_image_url = serializers.SerializerMethodField()

    class Meta:
        model = Banner
        fields = [
            'id', 'title', 'subtitle', 'description', 'banner_type', 'banner_type_display',
            'background_image', 'background_image_url', 'featured_image', 'featured_image_url',
            'text_color', 'overlay_opacity', 'cta_text', 'cta_link',
            'secondary_cta_text', 'secondary_cta_link', 'priority', 'is_active',
            'is_currently_active', 'start_date', 'end_date',
            'stat_1_value', 'stat_1_label', 'stat_2_value', 'stat_2_label',
            'stat_3_value', 'stat_3_label'
        ]

    def get_is_currently_active(self, obj):
        if not obj.is_active:
            return False
        now = timezone.now()
        if obj.start_date and now < obj.start_date:
            return False
        if obj.end_date and now > obj.end_date:
            return False
        return True

    def get_background_image_url(self, obj):
        if obj.background_image:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.background_image.url)
            return obj.background_image.url
        return None

    def get_featured_image_url(self, obj):
        if obj.featured_image:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.featured_image.url)
            return obj.featured_image.url
        return None


class BannerSimpleSerializer(serializers.ModelSerializer):
    """Minimal banner data"""
    background_image_url = serializers.SerializerMethodField()

    class Meta:
        model = Banner
        fields = ['id', 'title', 'subtitle', 'background_image_url', 'cta_text', 'cta_link']

    def get_background_image_url(self, obj):
        if obj.background_image:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.background_image.url)
            return obj.background_image.url
        return None


# ==================== COURSE ENQUIRY SERIALIZERS ====================

class CourseEnquiryCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating course enquiries from mobile app"""

    class Meta:
        model = CourseEnquiry
        fields = [
            'course', 'name', 'email', 'phone', 'current_qualification',
            'work_experience', 'current_company', 'preferred_batch',
            'preferred_contact_time', 'message'
        ]

    def validate(self, data):
        course = data.get('course')
        if course:
            # Check if course is published
            if not course.is_published:
                raise serializers.ValidationError({
                    'course': 'This course is not available for enquiries.'
                })

            # Allow enquiries for:
            # 1. 'enquiry_only' courses
            # 2. 'admin_only' courses
            # 3. Any course with allow_public_enrollment=False (admin-only enrollment)
            # 'online_purchase' courses with public enrollment should use direct enrollment
            allowed_types = ['enquiry_only', 'admin_only']
            is_admin_only_enrollment = not getattr(course, 'allow_public_enrollment', True)

            if hasattr(course, 'enrollment_type') and course.enrollment_type not in allowed_types and not is_admin_only_enrollment:
                raise serializers.ValidationError({
                    'course': 'This course is available for direct enrollment. Please enroll directly.'
                })
        return data


class CourseEnquiryListSerializer(serializers.ModelSerializer):
    """Serializer for listing course enquiries"""
    course_title = serializers.CharField(source='course.title', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    assigned_to_name = serializers.SerializerMethodField()

    class Meta:
        model = CourseEnquiry
        fields = [
            'id', 'course', 'course_title', 'name', 'email', 'phone',
            'status', 'status_display', 'assigned_to_name', 'created_at'
        ]

    def get_assigned_to_name(self, obj):
        if obj.assigned_to:
            return obj.assigned_to.name if hasattr(obj.assigned_to, 'name') else obj.assigned_to.username
        return None


class CourseEnquiryDetailSerializer(serializers.ModelSerializer):
    """Detailed serializer for course enquiries"""
    course_title = serializers.CharField(source='course.title', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    source_display = serializers.CharField(source='get_source_display', read_only=True)
    assigned_to_name = serializers.SerializerMethodField()

    class Meta:
        model = CourseEnquiry
        exclude = ['assigned_to', 'ip_address', 'user_agent']

    def get_assigned_to_name(self, obj):
        if obj.assigned_to:
            return obj.assigned_to.name if hasattr(obj.assigned_to, 'name') else obj.assigned_to.username
        return None


class StudentCourseEnquirySerializer(serializers.ModelSerializer):
    """Serializer for students to view their course enquiries"""
    course_title = serializers.CharField(source='course.title', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)

    class Meta:
        model = CourseEnquiry
        fields = [
            'id', 'course', 'course_title', 'name', 'email', 'phone',
            'status', 'status_display', 'message', 'created_at', 'updated_at'
        ]
        read_only_fields = ['__all__']


# ==================== ENHANCED DASHBOARD SERIALIZER ====================

class DashboardContentSerializer(serializers.Serializer):
    """Enhanced dashboard content for mobile app with all content types"""
    # News
    latest_news = NewsSimpleSerializer(many=True)

    # Placements
    recent_placements = PlacementSimpleSerializer(many=True)

    # Testimonials
    featured_testimonials = TestimonialSimpleSerializer(many=True)

    # Events (NEW)
    upcoming_events = EventSimpleSerializer(many=True)

    # Achievements (NEW)
    featured_achievements = AchievementSimpleSerializer(many=True)

    # Banners (NEW)
    active_banners = BannerSimpleSerializer(many=True)

    # User stats (NEW)
    learning_streak = serializers.IntegerField(default=0)
    total_learning_minutes = serializers.IntegerField(default=0)

    # Summary counts
    total_placements = serializers.IntegerField()
    total_testimonials = serializers.IntegerField()
    total_events = serializers.IntegerField(default=0)