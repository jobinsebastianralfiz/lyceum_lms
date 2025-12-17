from django.db import models
from django.contrib.auth import get_user_model
from django.core.validators import RegexValidator, URLValidator
import uuid

User = get_user_model()


class Lead(models.Model):
    """Model to collect leads for one-on-one sessions"""
    INTEREST_CHOICES = [
        ('web_development', 'Web Development'),
        ('mobile_development', 'Mobile Development'),
        ('data_science', 'Data Science'),
        ('ai_ml', 'AI/Machine Learning'),
        ('cybersecurity', 'Cybersecurity'),
        ('cloud_computing', 'Cloud Computing'),
        ('devops', 'DevOps'),
        ('other', 'Other'),
    ]
    
    STATUS_CHOICES = [
        ('new', 'New'),
        ('contacted', 'Contacted'),
        ('scheduled', 'Session Scheduled'),
        ('completed', 'Session Completed'),
        ('not_interested', 'Not Interested'),
        ('converted', 'Converted to Student'),
    ]
    
    EXPERIENCE_CHOICES = [
        ('beginner', 'Complete Beginner'),
        ('some_knowledge', 'Some Knowledge'),
        ('intermediate', 'Intermediate'),
        ('advanced', 'Advanced'),
        ('professional', 'Working Professional'),
    ]
    
    # Personal Information
    name = models.CharField(max_length=100)
    email = models.EmailField()
    phone = models.CharField(
        max_length=15, 
        validators=[RegexValidator(r'^\+?1?\d{9,15}$', 'Enter a valid phone number.')]
    )
    
    # Interest Details
    area_of_interest = models.CharField(max_length=50, choices=INTEREST_CHOICES)
    other_interest = models.CharField(max_length=100, blank=True, null=True, help_text="If 'Other' is selected")
    current_experience = models.CharField(max_length=50, choices=EXPERIENCE_CHOICES)
    
    # Goals and Expectations
    career_goals = models.TextField(help_text="What are your career goals?")
    learning_timeline = models.CharField(max_length=200, help_text="When do you want to achieve your goals?")
    budget_range = models.CharField(max_length=100, blank=True, null=True, help_text="Budget expectations")
    
    # Session Preferences
    preferred_time = models.CharField(max_length=100, help_text="Preferred time for session")
    specific_topics = models.TextField(blank=True, null=True, help_text="Any specific topics to discuss?")
    
    # Lead Management
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='new')
    notes = models.TextField(blank=True, null=True, help_text="Internal notes")
    assigned_to = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='assigned_leads')
    submitted_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='submitted_leads', help_text="User who submitted this lead (if authenticated)")
    
    # Tracking
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True, null=True)
    source = models.CharField(max_length=50, default='mobile_app', help_text="Where did the lead come from?")
    
    def __str__(self):
        return f"{self.name} - {self.area_of_interest} ({self.status})"
    
    @property
    def is_active(self):
        """Check if this lead is still active (allows new lead submissions)"""
        completed_statuses = ['completed', 'converted', 'not_interested']
        return self.status not in completed_statuses
    
    @property
    def allows_new_submission(self):
        """Check if user can submit a new lead (opposite of is_active)"""
        return not self.is_active
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['status']),
            models.Index(fields=['area_of_interest']),
            models.Index(fields=['created_at']),
        ]


class News(models.Model):
    """Model for latest news and updates"""
    CATEGORY_CHOICES = [
        ('general', 'General News'),
        ('course_update', 'Course Updates'),
        ('industry_news', 'Industry News'),
        ('company_news', 'Company News'),
        ('event', 'Events'),
        ('announcement', 'Announcements'),
    ]
    
    title = models.CharField(max_length=200)
    slug = models.SlugField(unique=True, blank=True)
    content = models.TextField()
    excerpt = models.TextField(max_length=300, help_text="Brief summary for cards/lists")
    
    # Media
    featured_image = models.ImageField(upload_to='news/images/', blank=True, null=True)
    thumbnail = models.ImageField(upload_to='news/thumbnails/', blank=True, null=True)
    
    # Organization
    category = models.CharField(max_length=20, choices=CATEGORY_CHOICES, default='general')
    tags = models.CharField(max_length=200, blank=True, null=True, help_text="Comma-separated tags")
    
    # SEO
    meta_title = models.CharField(max_length=60, blank=True, null=True)
    meta_description = models.CharField(max_length=160, blank=True, null=True)
    
    # Publishing
    is_published = models.BooleanField(default=False)
    is_featured = models.BooleanField(default=False, help_text="Show on homepage/featured section")
    published_at = models.DateTimeField(null=True, blank=True)
    
    # Tracking
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='created_news')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    view_count = models.PositiveIntegerField(default=0)
    
    def __str__(self):
        return self.title
    
    class Meta:
        ordering = ['-published_at', '-created_at']
        verbose_name_plural = "News"
        indexes = [
            models.Index(fields=['is_published', 'published_at']),
            models.Index(fields=['category']),
            models.Index(fields=['is_featured']),
        ]


class Placement(models.Model):
    """Model for student placement success stories"""
    PLACEMENT_TYPE_CHOICES = [
        ('full_time', 'Full Time Job'),
        ('internship', 'Internship'),
        ('freelance', 'Freelance Project'),
        ('startup', 'Started Own Company'),
        ('promotion', 'Job Promotion'),
    ]
    
    # Student Information
    student_name = models.CharField(max_length=100)
    student_photo = models.ImageField(upload_to='placements/photos/', blank=True, null=True)
    course_completed = models.CharField(max_length=100)
    batch_year = models.CharField(max_length=10)
    
    # Placement Details
    company_name = models.CharField(max_length=100)
    company_logo = models.ImageField(upload_to='placements/logos/', blank=True, null=True)
    job_title = models.CharField(max_length=100)
    placement_type = models.CharField(max_length=20, choices=PLACEMENT_TYPE_CHOICES)
    package_amount = models.DecimalField(max_digits=10, decimal_places=2, help_text="Annual package in currency")
    package_currency = models.CharField(max_length=10, default='INR')
    location = models.CharField(max_length=100)
    
    # Success Story
    success_story = models.TextField(help_text="Student's journey and success story")
    key_achievements = models.JSONField(default=list, help_text="List of key achievements")
    
    # Skills Used
    skills_gained = models.TextField(help_text="Skills learned during the course")
    technologies_used = models.CharField(max_length=300, help_text="Technologies used in current role")
    
    # Publishing
    is_published = models.BooleanField(default=False)
    is_featured = models.BooleanField(default=False)
    published_at = models.DateTimeField(null=True, blank=True)
    
    # Consent
    consent_given = models.BooleanField(default=False, help_text="Student consent to publish details")
    can_show_package = models.BooleanField(default=True, help_text="Can show package details publicly")
    
    # Tracking
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='created_placements')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"{self.student_name} - {self.company_name} ({self.job_title})"
    
    class Meta:
        ordering = ['-published_at', '-created_at']
        indexes = [
            models.Index(fields=['is_published', 'published_at']),
            models.Index(fields=['is_featured']),
            models.Index(fields=['placement_type']),
        ]


class Testimonial(models.Model):
    """Model for student testimonials - supports YouTube videos and text+image"""
    TESTIMONIAL_TYPE_CHOICES = [
        ('video_youtube', 'YouTube Video'),
        ('text_image', 'Text + Image'),
        ('video_upload', 'Uploaded Video'),
        ('audio', 'Audio Recording'),
    ]
    
    RATING_CHOICES = [
        (1, '1 Star'),
        (2, '2 Stars'),
        (3, '3 Stars'),
        (4, '4 Stars'),
        (5, '5 Stars'),
    ]
    
    # Basic Information
    student_name = models.CharField(max_length=100)
    student_photo = models.ImageField(upload_to='testimonials/photos/', blank=True, null=True)
    course_name = models.CharField(max_length=100)
    batch_year = models.CharField(max_length=10)
    
    # Testimonial Content
    testimonial_type = models.CharField(max_length=20, choices=TESTIMONIAL_TYPE_CHOICES)
    
    # Text Content (for text_image type)
    testimonial_text = models.TextField(blank=True, null=True, help_text="Written testimonial content")
    
    # Video Content (for YouTube and uploaded videos)
    youtube_url = models.URLField(blank=True, null=True, validators=[URLValidator()], 
                                  help_text="YouTube video URL")
    youtube_video_id = models.CharField(max_length=20, blank=True, null=True, 
                                        help_text="Extracted YouTube video ID")
    uploaded_video = models.FileField(upload_to='testimonials/videos/', blank=True, null=True)
    video_thumbnail = models.ImageField(upload_to='testimonials/thumbnails/', blank=True, null=True)
    
    # Audio Content (for audio type)
    audio_file = models.FileField(upload_to='testimonials/audio/', blank=True, null=True)
    
    # Rating and Feedback
    overall_rating = models.IntegerField(choices=RATING_CHOICES, default=5)
    course_rating = models.IntegerField(choices=RATING_CHOICES, default=5)
    instructor_rating = models.IntegerField(choices=RATING_CHOICES, default=5)
    
    # Additional Details
    key_learnings = models.TextField(blank=True, null=True, help_text="What did they learn?")
    career_impact = models.TextField(blank=True, null=True, help_text="How did it impact their career?")
    recommendation = models.TextField(blank=True, null=True, help_text="Would they recommend? Why?")
    
    # Current Status
    current_position = models.CharField(max_length=100, blank=True, null=True)
    current_company = models.CharField(max_length=100, blank=True, null=True)
    
    # Publishing
    is_published = models.BooleanField(default=False)
    is_featured = models.BooleanField(default=False, help_text="Show in featured testimonials")
    published_at = models.DateTimeField(null=True, blank=True)
    
    # Consent
    consent_given = models.BooleanField(default=False, help_text="Student consent to publish")
    can_show_details = models.BooleanField(default=True, help_text="Can show personal details")
    
    # Social Proof
    likes_count = models.PositiveIntegerField(default=0)
    shares_count = models.PositiveIntegerField(default=0)
    
    # Tracking
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='created_testimonials')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def save(self, *args, **kwargs):
        # Extract YouTube video ID from URL
        if self.youtube_url and (not self.youtube_video_id or kwargs.get('force_extract_id', False)):
            self.youtube_video_id = self.extract_youtube_video_id(self.youtube_url)
        super().save(*args, **kwargs)
    
    def extract_youtube_video_id(self, url):
        """Extract YouTube video ID from various YouTube URL formats"""
        import re
        if not url:
            return None
            
        # Multiple patterns to handle different YouTube URL formats
        patterns = [
            r'(?:youtube\.com\/watch\?v=)([^&\n?#]+)',           # https://youtube.com/watch?v=VIDEO_ID
            r'(?:youtu\.be\/)([^&\n?#]+)',                      # https://youtu.be/VIDEO_ID
            r'(?:youtube\.com\/embed\/)([^&\n?#]+)',            # https://youtube.com/embed/VIDEO_ID
            r'(?:youtube\.com\/v\/)([^&\n?#]+)',                # https://youtube.com/v/VIDEO_ID
            r'(?:youtube\.com\/shorts\/)([^&\n?#]+)',           # https://youtube.com/shorts/VIDEO_ID (NEW)
            r'(?:youtube\.com\/user\/\S+\#p\/\w\/\w\/)([^&\n?#]+)',  # Older format
        ]
        
        for pattern in patterns:
            match = re.search(pattern, url)
            if match:
                video_id = match.group(1)
                # Clean up any extra parameters
                if '&' in video_id:
                    video_id = video_id.split('&')[0]
                if '?' in video_id:
                    video_id = video_id.split('?')[0]
                return video_id
        
        return None
    
    def __str__(self):
        return f"{self.student_name} - {self.course_name} ({self.testimonial_type})"
    
    @property
    def youtube_thumbnail_url(self):
        """Get YouTube video thumbnail URL"""
        if self.youtube_video_id:
            return f"https://img.youtube.com/vi/{self.youtube_video_id}/maxresdefault.jpg"
        return None
    
    @property
    def youtube_embed_url(self):
        """Get YouTube embed URL"""
        if self.youtube_video_id:
            return f"https://www.youtube.com/embed/{self.youtube_video_id}"
        return None
    
    class Meta:
        ordering = ['-published_at', '-created_at']
        indexes = [
            models.Index(fields=['is_published', 'published_at']),
            models.Index(fields=['is_featured']),
            models.Index(fields=['testimonial_type']),
            models.Index(fields=['overall_rating']),
        ]


class Banner(models.Model):
    """Model for dynamic hero/banner content on landing page"""
    BANNER_TYPE_CHOICES = [
        ('hero', 'Main Hero Banner'),
        ('promo', 'Promotional Banner'),
        ('announcement', 'Announcement Banner'),
        ('seasonal', 'Seasonal/Holiday Banner'),
    ]

    # Basic Information
    title = models.CharField(max_length=100, help_text="Main heading text")
    subtitle = models.CharField(max_length=200, blank=True, null=True, help_text="Secondary heading text")
    description = models.TextField(blank=True, null=True, help_text="Supporting text/description")

    # Call to Action
    cta_text = models.CharField(max_length=50, blank=True, null=True, help_text="Button text (e.g., 'Explore Courses')")
    cta_link = models.CharField(max_length=200, blank=True, null=True, help_text="Button link URL or path")
    secondary_cta_text = models.CharField(max_length=50, blank=True, null=True, help_text="Secondary button text")
    secondary_cta_link = models.CharField(max_length=200, blank=True, null=True, help_text="Secondary button link")

    # Media
    background_image = models.ImageField(upload_to='banners/backgrounds/', blank=True, null=True)
    featured_image = models.ImageField(upload_to='banners/featured/', blank=True, null=True, help_text="Image displayed on the right side")

    # Styling
    banner_type = models.CharField(max_length=20, choices=BANNER_TYPE_CHOICES, default='hero')
    text_color = models.CharField(max_length=20, default='white', help_text="Text color (e.g., 'white', '#ffffff')")
    overlay_opacity = models.DecimalField(max_digits=3, decimal_places=2, default=0.5, help_text="Background overlay opacity (0-1)")

    # Stats/Highlights (shown in hero section)
    stat_1_value = models.CharField(max_length=20, blank=True, null=True, help_text="e.g., '500+'")
    stat_1_label = models.CharField(max_length=50, blank=True, null=True, help_text="e.g., 'Students Enrolled'")
    stat_2_value = models.CharField(max_length=20, blank=True, null=True)
    stat_2_label = models.CharField(max_length=50, blank=True, null=True)
    stat_3_value = models.CharField(max_length=20, blank=True, null=True)
    stat_3_label = models.CharField(max_length=50, blank=True, null=True)

    # Scheduling
    is_active = models.BooleanField(default=True)
    start_date = models.DateTimeField(null=True, blank=True, help_text="When to start showing this banner")
    end_date = models.DateTimeField(null=True, blank=True, help_text="When to stop showing this banner")
    priority = models.IntegerField(default=0, help_text="Higher priority banners show first")

    # Tracking
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='created_banners')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.title} ({self.banner_type})"

    class Meta:
        ordering = ['-priority', '-created_at']
        indexes = [
            models.Index(fields=['is_active', 'banner_type']),
            models.Index(fields=['priority']),
        ]


class Event(models.Model):
    """Model for events and webinars"""
    EVENT_TYPE_CHOICES = [
        ('webinar', 'Webinar'),
        ('workshop', 'Workshop'),
        ('seminar', 'Seminar'),
        ('hackathon', 'Hackathon'),
        ('meetup', 'Meetup'),
        ('conference', 'Conference'),
        ('open_day', 'Open Day'),
        ('other', 'Other'),
    ]

    STATUS_CHOICES = [
        ('upcoming', 'Upcoming'),
        ('ongoing', 'Ongoing'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
        ('postponed', 'Postponed'),
    ]

    # Basic Information
    title = models.CharField(max_length=200)
    slug = models.SlugField(unique=True, blank=True)
    description = models.TextField()
    short_description = models.CharField(max_length=300, help_text="Brief summary for cards/lists")

    # Event Details
    event_type = models.CharField(max_length=20, choices=EVENT_TYPE_CHOICES)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='upcoming')

    # Date & Time
    event_date = models.DateField()
    start_time = models.TimeField()
    end_time = models.TimeField(null=True, blank=True)
    timezone = models.CharField(max_length=50, default='Asia/Kolkata')

    # Location (for physical events)
    is_online = models.BooleanField(default=True)
    venue_name = models.CharField(max_length=200, blank=True, null=True)
    venue_address = models.TextField(blank=True, null=True)
    map_link = models.URLField(blank=True, null=True)

    # Online Event Details
    meeting_link = models.URLField(blank=True, null=True, help_text="Zoom/Meet/Teams link")
    meeting_password = models.CharField(max_length=50, blank=True, null=True)

    # Media
    featured_image = models.ImageField(upload_to='events/images/', blank=True, null=True)
    thumbnail = models.ImageField(upload_to='events/thumbnails/', blank=True, null=True)

    # Registration
    registration_required = models.BooleanField(default=True)
    registration_link = models.URLField(blank=True, null=True)
    max_attendees = models.PositiveIntegerField(null=True, blank=True)
    registration_deadline = models.DateTimeField(null=True, blank=True)

    # Speakers/Hosts
    speakers = models.TextField(blank=True, null=True, help_text="Speaker names and details (comma-separated or JSON)")

    # Publishing
    is_published = models.BooleanField(default=False)
    is_featured = models.BooleanField(default=False, help_text="Show on homepage")
    published_at = models.DateTimeField(null=True, blank=True)

    # SEO
    meta_title = models.CharField(max_length=60, blank=True, null=True)
    meta_description = models.CharField(max_length=160, blank=True, null=True)

    # Tracking
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='created_events')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    view_count = models.PositiveIntegerField(default=0)

    def __str__(self):
        return f"{self.title} - {self.event_date}"

    @property
    def is_upcoming(self):
        from django.utils import timezone
        return self.event_date >= timezone.now().date() and self.status == 'upcoming'

    class Meta:
        ordering = ['event_date', 'start_time']
        indexes = [
            models.Index(fields=['is_published', 'event_date']),
            models.Index(fields=['status']),
            models.Index(fields=['is_featured']),
            models.Index(fields=['event_type']),
        ]


class Achievement(models.Model):
    """Model for academy achievements and milestones"""
    ACHIEVEMENT_TYPE_CHOICES = [
        ('award', 'Award'),
        ('recognition', 'Recognition'),
        ('milestone', 'Milestone'),
        ('partnership', 'Partnership'),
        ('accreditation', 'Accreditation'),
        ('ranking', 'Ranking'),
    ]

    # Basic Information
    title = models.CharField(max_length=200)
    slug = models.SlugField(unique=True, blank=True)
    description = models.TextField()
    short_description = models.CharField(max_length=300, help_text="Brief summary for cards/lists")

    # Achievement Details
    achievement_type = models.CharField(max_length=20, choices=ACHIEVEMENT_TYPE_CHOICES)
    awarded_by = models.CharField(max_length=200, help_text="Organization that gave the award/recognition")
    achievement_date = models.DateField()

    # Media
    image = models.ImageField(upload_to='achievements/images/', blank=True, null=True)
    badge_icon = models.ImageField(upload_to='achievements/badges/', blank=True, null=True)
    certificate = models.FileField(upload_to='achievements/certificates/', blank=True, null=True)

    # Additional Info
    year = models.CharField(max_length=4)
    category = models.CharField(max_length=100, blank=True, null=True, help_text="e.g., 'Education', 'Technology'")

    # Publishing
    is_published = models.BooleanField(default=False)
    is_featured = models.BooleanField(default=False, help_text="Show on homepage")

    # Tracking
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='created_achievements')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.title} ({self.year})"

    class Meta:
        ordering = ['-achievement_date', '-created_at']
        indexes = [
            models.Index(fields=['is_published']),
            models.Index(fields=['is_featured']),
            models.Index(fields=['achievement_type']),
        ]


class LeadFollowUp(models.Model):
    """Track follow-up activities for leads"""
    FOLLOW_UP_TYPE_CHOICES = [
        ('call', 'Phone Call'),
        ('email', 'Email'),
        ('whatsapp', 'WhatsApp'),
        ('meeting', 'Meeting'),
        ('demo', 'Demo Session'),
    ]

    lead = models.ForeignKey(Lead, on_delete=models.CASCADE, related_name='follow_ups')
    follow_up_type = models.CharField(max_length=20, choices=FOLLOW_UP_TYPE_CHOICES)
    notes = models.TextField()
    scheduled_at = models.DateTimeField()
    completed_at = models.DateTimeField(null=True, blank=True)
    created_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='follow_ups_created')
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.lead.name} - {self.follow_up_type} on {self.scheduled_at.date()}"

    class Meta:
        ordering = ['-scheduled_at']


class CourseEnquiry(models.Model):
    """Model for course enquiries/leads from information-only courses"""
    STATUS_CHOICES = [
        ('new', 'New'),
        ('contacted', 'Contacted'),
        ('interested', 'Interested'),
        ('demo_scheduled', 'Demo Scheduled'),
        ('enrolled', 'Enrolled'),
        ('not_interested', 'Not Interested'),
        ('follow_up', 'Follow Up Required'),
    ]

    SOURCE_CHOICES = [
        ('website', 'Website'),
        ('mobile_app', 'Mobile App'),
        ('referral', 'Referral'),
        ('social_media', 'Social Media'),
        ('google_ads', 'Google Ads'),
        ('other', 'Other'),
    ]

    # Course reference
    course = models.ForeignKey(
        'courses.Course',
        on_delete=models.CASCADE,
        related_name='enquiries'
    )

    # Contact Information
    name = models.CharField(max_length=100)
    email = models.EmailField()
    phone = models.CharField(
        max_length=20,
        validators=[RegexValidator(r'^\+?\d{9,15}$', 'Enter a valid phone number (9-15 digits, optional + prefix).')]
    )

    # Enquiry Details
    message = models.TextField(blank=True, null=True, help_text="User's message or query")
    preferred_batch = models.CharField(max_length=100, blank=True, null=True, help_text="Preferred batch timing")
    preferred_contact_time = models.CharField(max_length=100, blank=True, null=True)

    # Background
    current_qualification = models.CharField(max_length=200, blank=True, null=True)
    work_experience = models.CharField(max_length=100, blank=True, null=True)
    current_company = models.CharField(max_length=200, blank=True, null=True)

    # Lead Management
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='new')
    source = models.CharField(max_length=20, choices=SOURCE_CHOICES, default='website')
    assigned_to = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='assigned_course_enquiries'
    )
    notes = models.TextField(blank=True, null=True, help_text="Internal notes")

    # If user is registered
    user = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='course_enquiries'
    )

    # Tracking
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True, null=True)
    utm_source = models.CharField(max_length=100, blank=True, null=True)
    utm_medium = models.CharField(max_length=100, blank=True, null=True)
    utm_campaign = models.CharField(max_length=100, blank=True, null=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.name} - {self.course.title} ({self.status})"

    class Meta:
        ordering = ['-created_at']
        verbose_name_plural = "Course Enquiries"
        indexes = [
            models.Index(fields=['status']),
            models.Index(fields=['course']),
            models.Index(fields=['created_at']),
        ]