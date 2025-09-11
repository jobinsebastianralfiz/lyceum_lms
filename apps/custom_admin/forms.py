from django import forms
from django.contrib.auth.forms import UserCreationForm, UserChangeForm
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from apps.users.models import User, Team, TeamMembership
from apps.youtube_integration.models import YouTubeChannelConfig, YouTubeVideo
from apps.payments.models import Enrollment, InstallmentPlan, Payment
from apps.courses.models import Course, Module, VideoLesson, Assignment, Quiz, QuizQuestion, QuizChoice

class CustomUserCreationForm(UserCreationForm):
    """Custom form for creating new users"""
    
    name = forms.CharField(
        max_length=150,
        required=True,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter full name'
        }),
        help_text='Full name of the user'
    )
    
    email = forms.EmailField(
        required=True,
        widget=forms.EmailInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter email address'
        }),
        help_text='Valid email address'
    )
    
    username = forms.CharField(
        max_length=150,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter username (optional)'
        }),
        help_text='Optional username. If not provided, email will be used.'
    )
    
    role = forms.ChoiceField(
        choices=User.ROLE_CHOICES,
        initial='student',
        widget=forms.Select(attrs={
            'class': 'form-select'
        }),
        help_text='Select user role'
    )
    
    phone_number = forms.CharField(
        max_length=15,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter phone number'
        }),
        help_text='Optional phone number'
    )
    
    address = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 3,
            'placeholder': 'Enter address'
        }),
        help_text='Optional address'
    )
    
    is_staff = forms.BooleanField(
        required=False,
        widget=forms.CheckboxInput(attrs={
            'class': 'form-check-input'
        }),
        help_text='Designates whether the user can log into this admin site.'
    )
    
    is_active = forms.BooleanField(
        initial=True,
        required=False,
        widget=forms.CheckboxInput(attrs={
            'class': 'form-check-input'
        }),
        help_text='Designates whether this user should be treated as active.'
    )
    
    password1 = forms.CharField(
        label='Password',
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter password'
        }),
        help_text='Enter a strong password'
    )
    
    password2 = forms.CharField(
        label='Password confirmation',
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Confirm password'
        }),
        help_text='Enter the same password as before, for verification.'
    )

    class Meta:
        model = User
        fields = ('username', 'email', 'name', 'role', 'phone_number', 'address', 
                  'is_staff', 'is_active', 'password1', 'password2')

    def clean_email(self):
        email = self.cleaned_data.get('email')
        if User.objects.filter(email=email).exists():
            raise ValidationError('A user with this email already exists.')
        return email

    def clean_username(self):
        username = self.cleaned_data.get('username')
        if username and User.objects.filter(username=username).exists():
            raise ValidationError('A user with this username already exists.')
        return username

    def save(self, commit=True):
        user = super().save(commit=False)
        if not user.username:
            user.username = user.email
        if commit:
            user.save()
        return user


class CustomUserChangeForm(UserChangeForm):
    """Custom form for editing existing users"""
    
    name = forms.CharField(
        max_length=150,
        required=True,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter full name'
        }),
        help_text='Full name of the user'
    )
    
    email = forms.EmailField(
        required=True,
        widget=forms.EmailInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter email address'
        }),
        help_text='Valid email address'
    )
    
    username = forms.CharField(
        max_length=150,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter username (optional)'
        }),
        help_text='Optional username. If not provided, email will be used.'
    )
    
    role = forms.ChoiceField(
        choices=User.ROLE_CHOICES,
        widget=forms.Select(attrs={
            'class': 'form-select'
        }),
        help_text='Select user role'
    )
    
    phone_number = forms.CharField(
        max_length=15,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter phone number'
        }),
        help_text='Optional phone number'
    )
    
    address = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 3,
            'placeholder': 'Enter address'
        }),
        help_text='Optional address'
    )
    
    is_staff = forms.BooleanField(
        required=False,
        widget=forms.CheckboxInput(attrs={
            'class': 'form-check-input'
        }),
        help_text='Designates whether the user can log into this admin site.'
    )
    
    is_active = forms.BooleanField(
        required=False,
        widget=forms.CheckboxInput(attrs={
            'class': 'form-check-input'
        }),
        help_text='Designates whether this user should be treated as active.'
    )
    
    is_superuser = forms.BooleanField(
        required=False,
        widget=forms.CheckboxInput(attrs={
            'class': 'form-check-input'
        }),
        help_text='Designates that this user has all permissions without explicitly assigning them.'
    )

    class Meta:
        model = User
        fields = ('username', 'email', 'name', 'role', 'phone_number', 'address', 
                  'is_staff', 'is_active', 'is_superuser')

    def clean_email(self):
        email = self.cleaned_data.get('email')
        if User.objects.filter(email=email).exclude(pk=self.instance.pk).exists():
            raise ValidationError('A user with this email already exists.')
        return email

    def clean_username(self):
        username = self.cleaned_data.get('username')
        if username and User.objects.filter(username=username).exclude(pk=self.instance.pk).exists():
            raise ValidationError('A user with this username already exists.')
        return username

    def save(self, commit=True):
        user = super().save(commit=False)
        if not user.username:
            user.username = user.email
        if commit:
            user.save()
        return user

class CustomTeamForm(forms.ModelForm):
    """Custom form for creating and editing teams"""
    
    name = forms.CharField(
        max_length=100,
        required=True,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter team name'
        }),
        help_text='Team name (required)'
    )
    
    description = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 3,
            'placeholder': 'Enter team description'
        }),
        help_text='Optional team description'
    )
    
    team_leader = forms.ModelChoiceField(
        queryset=User.objects.all(),
        required=False,
        empty_label="Select team leader (optional)",
        widget=forms.Select(attrs={
            'class': 'form-select'
        }),
        help_text='Optional team leader'
    )
    
    max_members = forms.IntegerField(
        initial=5,
        min_value=1,
        max_value=100,
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter maximum members'
        }),
        help_text='Maximum number of team members (1-100)'
    )
    
    is_active = forms.BooleanField(
        initial=True,
        required=False,
        widget=forms.CheckboxInput(attrs={
            'class': 'form-check-input'
        }),
        help_text='Designates whether this team is active'
    )
    
    created_by = forms.ModelChoiceField(
        queryset=User.objects.filter(is_staff=True),
        widget=forms.Select(attrs={
            'class': 'form-select'
        }),
        help_text='Staff member who created this team'
    )

    class Meta:
        model = Team
        fields = ('name', 'description', 'team_leader', 'max_members', 'is_active', 'created_by')

    def clean_name(self):
        name = self.cleaned_data.get('name')
        if Team.objects.filter(name=name).exclude(pk=self.instance.pk if self.instance else None).exists():
            raise ValidationError('A team with this name already exists.')
        return name


class CustomTeamMembershipForm(forms.ModelForm):
    """Custom form for creating and editing team memberships"""
    
    team = forms.ModelChoiceField(
        queryset=Team.objects.filter(is_active=True),
        widget=forms.Select(attrs={
            'class': 'form-select'
        }),
        help_text='Select the team'
    )
    
    user = forms.ModelChoiceField(
        queryset=User.objects.filter(is_active=True),
        widget=forms.Select(attrs={
            'class': 'form-select'
        }),
        help_text='Select the user to add to the team'
    )
    
    role = forms.ChoiceField(
        choices=TeamMembership.ROLE_CHOICES,
        initial='member',
        widget=forms.Select(attrs={
            'class': 'form-select'
        }),
        help_text='Select the role for this member'
    )
    
    is_active = forms.BooleanField(
        initial=True,
        required=False,
        widget=forms.CheckboxInput(attrs={
            'class': 'form-check-input'
        }),
        help_text='Designates whether this membership is active'
    )

    class Meta:
        model = TeamMembership
        fields = ('team', 'user', 'role', 'is_active')

    def clean(self):
        cleaned_data = super().clean()
        team = cleaned_data.get('team')
        user = cleaned_data.get('user')
        
        if team and user:
            # Check if user is already a member of this team
            existing_membership = TeamMembership.objects.filter(
                team=team, 
                user=user
            ).exclude(pk=self.instance.pk if self.instance else None)
            
            if existing_membership.exists():
                raise ValidationError('This user is already a member of this team.')
            
            # Check if team has space for new members
            if not self.instance and team.is_full:
                raise ValidationError(f'Team "{team.name}" is full. Maximum members: {team.max_members}')
        
        return cleaned_data

class CustomYouTubeChannelConfigForm(forms.ModelForm):
    """Custom form for creating and editing YouTube channel configurations"""
    
    admin_user = forms.ModelChoiceField(
        queryset=User.objects.filter(is_staff=True),
        widget=forms.Select(attrs={
            'class': 'form-select'
        }),
        help_text='Staff member managing this channel'
    )
    
    channel_id = forms.CharField(
        max_length=50,
        required=True,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter YouTube channel ID'
        }),
        help_text='YouTube channel ID (e.g., UCxxxxxxxxxxxxxxxxxxxxxx)'
    )
    
    channel_name = forms.CharField(
        max_length=200,
        required=True,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter channel name'
        }),
        help_text='Display name of the YouTube channel'
    )
    
    access_token = forms.CharField(
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 3,
            'placeholder': 'Enter YouTube API access token'
        }),
        help_text='OAuth2 access token for YouTube API'
    )
    
    refresh_token = forms.CharField(
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 3,
            'placeholder': 'Enter refresh token'
        }),
        help_text='OAuth2 refresh token for YouTube API'
    )

    class Meta:
        model = YouTubeChannelConfig
        fields = ('admin_user', 'channel_id', 'channel_name', 'access_token', 'refresh_token')

    def clean_channel_id(self):
        channel_id = self.cleaned_data.get('channel_id')
        existing_config = YouTubeChannelConfig.objects.filter(
            channel_id=channel_id
        ).exclude(pk=self.instance.pk if self.instance else None)
        
        if existing_config.exists():
            raise ValidationError('A configuration for this channel already exists.')
        return channel_id


class CustomYouTubeVideoForm(forms.ModelForm):
    """Custom form for creating and editing YouTube videos"""
    
    video_id = forms.CharField(
        max_length=20,
        required=True,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter YouTube video ID'
        }),
        help_text='YouTube video ID (e.g., dQw4w9WgXcQ)'
    )
    
    title = forms.CharField(
        max_length=300,
        required=True,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter video title'
        }),
        help_text='Title of the YouTube video'
    )
    
    description = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 4,
            'placeholder': 'Enter video description'
        }),
        help_text='Optional video description'
    )
    
    thumbnail_url = forms.URLField(
        required=True,
        widget=forms.URLInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter thumbnail URL'
        }),
        help_text='URL of the video thumbnail image'
    )
    
    duration = forms.IntegerField(
        min_value=1,
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'placeholder': 'Duration in seconds'
        }),
        help_text='Video duration in seconds'
    )
    
    published_at = forms.DateTimeField(
        widget=forms.DateTimeInput(attrs={
            'class': 'form-control',
            'type': 'datetime-local'
        }),
        help_text='When the video was published on YouTube'
    )
    
    channel_config = forms.ModelChoiceField(
        queryset=YouTubeChannelConfig.objects.all(),
        widget=forms.Select(attrs={
            'class': 'form-select'
        }),
        help_text='YouTube channel this video belongs to'
    )
    
    is_available = forms.BooleanField(
        initial=True,
        required=False,
        widget=forms.CheckboxInput(attrs={
            'class': 'form-check-input'
        }),
        help_text='Whether this video is available in the system'
    )

    class Meta:
        model = YouTubeVideo
        fields = ('video_id', 'title', 'description', 'thumbnail_url', 'duration', 
                  'published_at', 'channel_config', 'is_available')

    def clean_video_id(self):
        video_id = self.cleaned_data.get('video_id')
        existing_video = YouTubeVideo.objects.filter(
            video_id=video_id
        ).exclude(pk=self.instance.pk if self.instance else None)
        
        if existing_video.exists():
            raise ValidationError('A video with this ID already exists.')
        return video_id

    def clean_duration(self):
        duration = self.cleaned_data.get('duration')
        if duration and duration <= 0:
            raise ValidationError('Duration must be greater than 0 seconds.')
        return duration


class CustomEnrollmentForm(forms.ModelForm):
    """Custom form for creating and editing enrollments"""
    
    user = forms.ModelChoiceField(
        queryset=User.objects.filter(is_active=True),
        widget=forms.Select(attrs={
            'class': 'form-select'
        }),
        help_text='Student to enroll in the course'
    )
    
    course = forms.ModelChoiceField(
        queryset=Course.objects.filter(is_published=True),
        widget=forms.Select(attrs={
            'class': 'form-select'
        }),
        help_text='Course to enroll the student in (includes both public and admin-only courses)'
    )
    
    enrollment_type = forms.ChoiceField(
        choices=Enrollment.ENROLLMENT_TYPE_CHOICES,
        initial='individual',
        widget=forms.Select(attrs={
            'class': 'form-select'
        }),
        help_text='Type of enrollment'
    )
    
    team = forms.ModelChoiceField(
        queryset=Team.objects.filter(is_active=True),
        required=False,
        empty_label="Select team (for team enrollments)",
        widget=forms.Select(attrs={
            'class': 'form-select'
        }),
        help_text='Team for team enrollments (optional)'
    )
    
    total_amount = forms.DecimalField(
        max_digits=10,
        decimal_places=2,
        min_value=0,
        required=False,
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'step': '0.01',
            'placeholder': 'Enter total amount (auto-filled for free courses)'
        }),
        help_text='Total enrollment amount including tax (auto-populated based on course)'
    )
    
    tax_amount = forms.DecimalField(
        max_digits=10,
        decimal_places=2,
        min_value=0,
        initial=0,
        required=False,
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'step': '0.01',
            'placeholder': 'Enter tax amount (auto-filled for free courses)'
        }),
        help_text='Tax amount for this enrollment (auto-populated based on course)'
    )
    
    payment_status = forms.ChoiceField(
        choices=Enrollment.PAYMENT_STATUS_CHOICES,
        initial='pending',
        widget=forms.Select(attrs={
            'class': 'form-select'
        }),
        help_text='Current payment status'
    )
    
    has_installment_plan = forms.BooleanField(
        required=False,
        widget=forms.CheckboxInput(attrs={
            'class': 'form-check-input'
        }),
        help_text='Check this to create an installment plan after saving the enrollment'
    )
    
    active = forms.BooleanField(
        initial=True,
        required=False,
        widget=forms.CheckboxInput(attrs={
            'class': 'form-check-input'
        }),
        help_text='Whether this enrollment is active'
    )

    class Meta:
        model = Enrollment
        fields = ('user', 'course', 'enrollment_type', 'team', 'total_amount', 
                  'tax_amount', 'payment_status', 'has_installment_plan', 'active')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Set course pricing as default values if creating new enrollment
        if not self.instance.pk and 'course' in self.data:
            try:
                course = Course.objects.get(pk=self.data['course'])
                if course.is_free_course:
                    # Free course - set to 0 and hide fields
                    self.fields['total_amount'].initial = 0
                    self.fields['tax_amount'].initial = 0
                    self.fields['payment_status'].initial = 'free'
                    self.fields['total_amount'].widget.attrs['readonly'] = True
                    self.fields['tax_amount'].widget.attrs['readonly'] = True
                else:
                    # Paid course - set to course prices
                    self.fields['total_amount'].initial = course.total_price
                    self.fields['tax_amount'].initial = course.tax_amount
                    self.fields['payment_status'].initial = 'pending'
            except (Course.DoesNotExist, ValueError):
                pass

    def clean(self):
        cleaned_data = super().clean()
        user = cleaned_data.get('user')
        course = cleaned_data.get('course')
        enrollment_type = cleaned_data.get('enrollment_type')
        team = cleaned_data.get('team')
        total_amount = cleaned_data.get('total_amount')
        tax_amount = cleaned_data.get('tax_amount')
        payment_status = cleaned_data.get('payment_status')
        
        if user and course:
            # Check if user is already enrolled in this course
            existing_enrollment = Enrollment.objects.filter(
                user=user, 
                course=course
            ).exclude(pk=self.instance.pk if self.instance else None)
            
            if existing_enrollment.exists():
                raise ValidationError('This user is already enrolled in this course.')
            
            # Auto-populate pricing based on course for free courses
            if course.is_free_course:
                cleaned_data['total_amount'] = 0
                cleaned_data['tax_amount'] = 0
                cleaned_data['payment_status'] = 'free'
            elif total_amount is None or tax_amount is None:
                # Auto-populate for paid courses if not provided
                cleaned_data['total_amount'] = course.total_price
                cleaned_data['tax_amount'] = course.tax_amount
                if not payment_status:
                    cleaned_data['payment_status'] = 'pending'
        
        # Validate team enrollment
        if enrollment_type == 'team':
            if not team:
                raise ValidationError('Team is required for team enrollments.')
        elif enrollment_type != 'team' and team:
            # Clear team if not team enrollment
            cleaned_data['team'] = None
        
        # Validate tax amount doesn't exceed total amount
        final_total = cleaned_data.get('total_amount', 0) or 0
        final_tax = cleaned_data.get('tax_amount', 0) or 0
        if final_tax > final_total:
            raise ValidationError('Tax amount cannot exceed total amount.')
        
        return cleaned_data

    def clean_user(self):
        user = self.cleaned_data.get('user')
        if user and not user.is_active:
            raise ValidationError('Cannot enroll inactive users.')
        return user

    def clean_course(self):
        course = self.cleaned_data.get('course')
        if course and not course.is_published:
            raise ValidationError('Cannot enroll in unpublished courses.')
        return course


class CustomInstallmentPlanForm(forms.ModelForm):
    """Custom form for creating and editing installment plans"""
    
    enrollment = forms.ModelChoiceField(
        queryset=Enrollment.objects.select_related('user', 'course').filter(
            payment_status__in=['pending', 'partial'],
            installment_plan_details__isnull=True
        ),
        widget=forms.Select(attrs={
            'class': 'form-select'
        }),
        help_text='Select enrollment that needs an installment plan'
    )
    
    total_installments = forms.IntegerField(
        min_value=2,
        max_value=24,
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter number of installments'
        }),
        help_text='Total number of installments (2-24)'
    )
    
    installment_amount = forms.DecimalField(
        max_digits=10,
        decimal_places=2,
        min_value=0.01,
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'step': '0.01',
            'placeholder': 'Enter installment amount'
        }),
        help_text='Amount per installment'
    )
    
    frequency = forms.ChoiceField(
        choices=InstallmentPlan.FREQUENCY_CHOICES,
        initial='monthly',
        widget=forms.Select(attrs={
            'class': 'form-select'
        }),
        help_text='Payment frequency'
    )
    
    start_date = forms.DateField(
        widget=forms.DateInput(attrs={
            'class': 'form-control',
            'type': 'date'
        }),
        help_text='Date when first installment is due'
    )

    class Meta:
        model = InstallmentPlan
        fields = ('enrollment', 'total_installments', 'installment_amount', 'frequency', 'start_date')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # If editing existing plan, include current enrollment even if it has installment plan
        if self.instance and self.instance.pk:
            self.fields['enrollment'].queryset = Enrollment.objects.select_related('user', 'course').all()
        
        # Set default start date to today
        if not self.instance.pk:
            from datetime import date
            self.fields['start_date'].initial = date.today()

    def clean(self):
        from decimal import Decimal
        
        cleaned_data = super().clean()
        enrollment = cleaned_data.get('enrollment')
        total_installments = cleaned_data.get('total_installments')
        installment_amount = cleaned_data.get('installment_amount')
        
        if enrollment and total_installments and installment_amount:
            # Calculate total plan amount
            total_plan_amount = total_installments * installment_amount
            
            # Check if total plan amount matches or is reasonable compared to enrollment amount
            enrollment_total = enrollment.total_amount or Decimal('0')
            
            # Convert to Decimal for proper calculation
            margin_high = enrollment_total * Decimal('1.1')  # Allow 10% margin for flexibility
            margin_low = enrollment_total * Decimal('0.5')   # Must be at least 50% of enrollment
            
            if total_plan_amount > margin_high:
                raise ValidationError(
                    f'Total installment amount (₹{total_plan_amount:.2f}) exceeds enrollment amount (₹{enrollment_total:.2f}) by more than 10%.'
                )
            
            if total_plan_amount < margin_low:
                raise ValidationError(
                    f'Total installment amount (₹{total_plan_amount:.2f}) is too low compared to enrollment amount (₹{enrollment_total:.2f}).'
                )
        
        return cleaned_data

    def clean_enrollment(self):
        enrollment = self.cleaned_data.get('enrollment')
        
        if enrollment:
            # Check if enrollment already has installment plan (for new plans only)
            if not self.instance.pk and enrollment.has_installment_plan:
                try:
                    existing_plan = InstallmentPlan.objects.get(enrollment=enrollment)
                    raise ValidationError(f'This enrollment already has an installment plan (ID: {existing_plan.id}).')
                except InstallmentPlan.DoesNotExist:
                    # Update the enrollment's has_installment_plan flag
                    enrollment.has_installment_plan = False
                    enrollment.save()
            
            # Check if enrollment is in a valid state for installment plan
            if enrollment.payment_status == 'completed':
                raise ValidationError('Cannot create installment plan for completed payments.')
            
            if enrollment.payment_status == 'free':
                raise ValidationError('Cannot create installment plan for free enrollments.')
        
        return enrollment

    def save(self, commit=True):
        instance = super().save(commit=False)
        
        if commit:
            instance.save()
            # Update enrollment to indicate it has installment plan
            instance.enrollment.has_installment_plan = True
            instance.enrollment.save()
        
        return instance


class CustomVideoLessonForm(forms.ModelForm):
    """Enhanced form for creating and editing video lessons with platform support"""

    class Meta:
        model = VideoLesson
        fields = ('module', 'title', 'platform', 'video_url', 'video_id', 'vimeo_video_id',
                  'youtube_video_id', 'youtube_url', 'thumbnail_url', 
                  'duration', 'description', 'resource_file', 'order', 'is_preview')
        widgets = {
            'module': forms.Select(attrs={'class': 'form-select'}),
            'title': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Enter video lesson title'}),
            'platform': forms.Select(attrs={'class': 'form-select'}),
            'video_url': forms.URLInput(attrs={'class': 'form-control', 'placeholder': 'Full video URL'}),
            'video_id': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Platform video ID'}),
            'vimeo_video_id': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Vimeo video ID'}),
            'youtube_url': forms.URLInput(attrs={'class': 'form-control', 'placeholder': 'https://www.youtube.com/watch?v=...'}),
            'youtube_video_id': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Enter YouTube video ID'}),
            'thumbnail_url': forms.URLInput(attrs={'class': 'form-control', 'placeholder': 'Thumbnail URL (auto-generated if empty)'}),
            'duration': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'Duration in seconds'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 4, 'placeholder': 'Describe what students will learn'}),
            'resource_file': forms.FileInput(attrs={'class': 'form-control'}),
            'order': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': '1'}),
            'is_preview': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Make module queryset more organized
        self.fields['module'].queryset = Module.objects.select_related('course').all().order_by('course__title', 'order')
        
        # Set help texts
        self.fields['youtube_url'].help_text = 'Full YouTube URL (optional if video ID provided)'
        self.fields['youtube_video_id'].help_text = 'YouTube video ID (optional if URL provided)'
        self.fields['thumbnail_url'].help_text = 'Auto-generated from YouTube if not provided'
        self.fields['duration'].help_text = 'Video duration in seconds'
        self.fields['order'].help_text = 'Order of lesson in the module'
        self.fields['is_preview'].help_text = 'Available as free preview for non-enrolled students'

    def clean(self):
        cleaned_data = super().clean()
        youtube_url = cleaned_data.get('youtube_url', '').strip()
        youtube_video_id = cleaned_data.get('youtube_video_id', '').strip()
        
        # At least one of YouTube URL or video ID must be provided
        if not youtube_url and not youtube_video_id:
            raise ValidationError('Either YouTube URL or YouTube video ID must be provided.')
        
        # Extract video ID from URL if URL is provided but ID is not
        if youtube_url and not youtube_video_id:
            video_id = self.extract_youtube_id(youtube_url)
            if video_id:
                cleaned_data['youtube_video_id'] = video_id
            else:
                raise ValidationError(f'Could not extract video ID from URL: {youtube_url}')
        
        # Generate thumbnail URL if not provided and video ID exists
        final_video_id = cleaned_data.get('youtube_video_id')
        if final_video_id and not cleaned_data.get('thumbnail_url'):
            cleaned_data['thumbnail_url'] = f'https://img.youtube.com/vi/{final_video_id}/maxresdefault.jpg'
        
        return cleaned_data

    def extract_youtube_id(self, url):
        """Extract YouTube video ID from various YouTube URL formats"""
        import re
        url = url.strip()
        patterns = [
            r'(?:https?://)?(?:www\.)?youtube\.com/watch\?v=([a-zA-Z0-9_-]{11})',
            r'(?:https?://)?(?:www\.)?youtu\.be/([a-zA-Z0-9_-]{11})',
            r'(?:https?://)?(?:www\.)?youtube\.com/embed/([a-zA-Z0-9_-]{11})',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, url)
            if match and len(match.group(1)) == 11:
                return match.group(1)
        return None


class CustomAssignmentForm(forms.ModelForm):
    """Custom form for creating and editing assignments"""

    class Meta:
        model = Assignment
        fields = ('module', 'title', 'description', 'requirements', 'resources', 
                  'max_points', 'passing_score', 'due_days', 'is_required', 'order')
        widgets = {
            'module': forms.Select(attrs={'class': 'form-select'}),
            'title': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Enter assignment title'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 4, 'placeholder': 'Describe what students need to accomplish'}),
            'requirements': forms.Textarea(attrs={'class': 'form-control', 'rows': 6, 'placeholder': 'List specific requirements, technologies, or constraints'}),
            'resources': forms.Textarea(attrs={'class': 'form-control', 'rows': 6, 'placeholder': 'Provide helpful links, documentation, or additional resources'}),
            'max_points': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': '100'}),
            'passing_score': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': '70'}),
            'due_days': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': '7'}),
            'is_required': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'order': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': '1'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Make module queryset more organized
        self.fields['module'].queryset = Module.objects.select_related('course').all().order_by('course__title', 'order')
        
        # Set help texts
        self.fields['module'].help_text = 'Select the module this assignment belongs to'
        self.fields['title'].help_text = 'Title of the assignment'
        self.fields['description'].help_text = 'Assignment instructions and requirements'
        self.fields['requirements'].help_text = 'Specific requirements (e.g., "Create a Python script that...")'
        self.fields['resources'].help_text = 'Additional resources or links'
        self.fields['max_points'].help_text = 'Maximum points for this assignment'
        self.fields['passing_score'].help_text = 'Minimum score to pass'
        self.fields['due_days'].help_text = 'Days from module start to complete assignment'
        self.fields['is_required'].help_text = 'Required to proceed to next module'
        self.fields['order'].help_text = 'Order within the module'

    def clean(self):
        cleaned_data = super().clean()
        max_points = cleaned_data.get('max_points')
        passing_score = cleaned_data.get('passing_score')
        
        # Validate that passing score doesn't exceed max points
        if max_points and passing_score and passing_score > max_points:
            raise ValidationError('Passing score cannot exceed maximum points.')
        
        return cleaned_data

    def clean_order(self):
        order = self.cleaned_data.get('order')
        module = self.cleaned_data.get('module')
        
        if order and module:
            # Check if another assignment in the same module already has this order
            existing_assignment = Assignment.objects.filter(
                module=module,
                order=order
            ).exclude(pk=self.instance.pk if self.instance else None)
            
            if existing_assignment.exists():
                raise ValidationError(f'An assignment with order {order} already exists in this module.')
        
        return order


class CustomQuizQuestionForm(forms.ModelForm):
    """Custom form for creating and editing quiz questions"""

    class Meta:
        model = QuizQuestion
        fields = ('quiz', 'question_text', 'question_type', 'points', 'explanation', 'order')
        widgets = {
            'quiz': forms.Select(attrs={'class': 'form-select'}),
            'question_text': forms.Textarea(attrs={'class': 'form-control', 'rows': 4, 'placeholder': 'Enter the question text'}),
            'question_type': forms.Select(attrs={'class': 'form-select'}),
            'points': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': '1'}),
            'explanation': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Explanation shown after answering (optional)'}),
            'order': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': '1'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Set help texts
        self.fields['quiz'].help_text = 'Select the quiz this question belongs to'
        self.fields['question_text'].help_text = 'The question text that students will see'
        self.fields['question_type'].help_text = 'Type of question'
        self.fields['points'].help_text = 'Points awarded for correct answer'
        self.fields['explanation'].help_text = 'Optional explanation shown after answering'
        self.fields['order'].help_text = 'Order of question in the quiz'

    def clean_order(self):
        order = self.cleaned_data.get('order')
        quiz = self.cleaned_data.get('quiz')
        
        if order and quiz:
            # Check if another question in the same quiz already has this order
            existing_question = QuizQuestion.objects.filter(
                quiz=quiz,
                order=order
            ).exclude(pk=self.instance.pk if self.instance else None)
            
            if existing_question.exists():
                raise ValidationError(f'A question with order {order} already exists in this quiz.')
        
        return order


class CustomQuizChoiceForm(forms.ModelForm):
    """Custom form for creating and editing quiz choices"""

    class Meta:
        model = QuizChoice
        fields = ('question', 'choice_text', 'is_correct', 'order')
        widgets = {
            'question': forms.Select(attrs={'class': 'form-select'}),
            'choice_text': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Enter the choice text'}),
            'is_correct': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'order': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': '1'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Set help texts
        self.fields['question'].help_text = 'Select the question this choice belongs to'
        self.fields['choice_text'].help_text = 'The choice text that students will see'
        self.fields['is_correct'].help_text = 'Mark this as the correct answer'
        self.fields['order'].help_text = 'Order of choice in the question'

    def clean_order(self):
        order = self.cleaned_data.get('order')
        question = self.cleaned_data.get('question')
        
        if order and question:
            # Check if another choice in the same question already has this order
            existing_choice = QuizChoice.objects.filter(
                question=question,
                order=order
            ).exclude(pk=self.instance.pk if self.instance else None)
            
            if existing_choice.exists():
                raise ValidationError(f'A choice with order {order} already exists in this question.')
        
        return order


class CustomQuizQuestionWithChoicesForm(forms.ModelForm):
    """Enhanced form for creating quiz questions with choices in one step"""
    
    # Choice fields (up to 6 choices)
    choice_1 = forms.CharField(max_length=500, required=False, widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Enter choice 1'}))
    choice_2 = forms.CharField(max_length=500, required=False, widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Enter choice 2'}))
    choice_3 = forms.CharField(max_length=500, required=False, widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Enter choice 3'}))
    choice_4 = forms.CharField(max_length=500, required=False, widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Enter choice 4'}))
    choice_5 = forms.CharField(max_length=500, required=False, widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Enter choice 5 (optional)'}))
    choice_6 = forms.CharField(max_length=500, required=False, widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Enter choice 6 (optional)'}))
    
    # Correct answer selection
    correct_choice = forms.ChoiceField(
        choices=[
            ('1', 'Choice 1'),
            ('2', 'Choice 2'), 
            ('3', 'Choice 3'),
            ('4', 'Choice 4'),
            ('5', 'Choice 5'),
            ('6', 'Choice 6'),
        ],
        widget=forms.RadioSelect(attrs={'class': 'form-check-input'}),
        help_text='Select which choice is the correct answer'
    )

    class Meta:
        model = QuizQuestion
        fields = ('quiz', 'question_text', 'question_type', 'points', 'explanation', 'order')
        widgets = {
            'quiz': forms.Select(attrs={'class': 'form-select'}),
            'question_text': forms.Textarea(attrs={'class': 'form-control', 'rows': 4, 'placeholder': 'Enter the question text'}),
            'question_type': forms.Select(attrs={'class': 'form-select'}),
            'points': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': '1'}),
            'explanation': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Explanation shown after answering (optional)'}),
            'order': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': '1'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Set help texts
        self.fields['quiz'].help_text = 'Select the quiz this question belongs to'
        self.fields['question_text'].help_text = 'The question text that students will see'
        self.fields['question_type'].help_text = 'Type of question'
        self.fields['points'].help_text = 'Points awarded for correct answer'
        self.fields['explanation'].help_text = 'Optional explanation shown after answering'
        self.fields['order'].help_text = 'Order of question in the quiz'

    def clean(self):
        cleaned_data = super().clean()
        question_type = cleaned_data.get('question_type')
        
        # For multiple choice questions, ensure we have at least 2 choices
        if question_type == 'multiple_choice':
            choices = []
            for i in range(1, 7):
                choice_text = cleaned_data.get(f'choice_{i}', '').strip()
                if choice_text:
                    choices.append(choice_text)
            
            if len(choices) < 2:
                raise ValidationError('Multiple choice questions must have at least 2 answer choices.')
            
            correct_choice = cleaned_data.get('correct_choice')
            if correct_choice and int(correct_choice) > len(choices):
                raise ValidationError('The selected correct answer choice does not exist.')
        
        return cleaned_data

    def save(self, commit=True):
        question = super().save(commit=commit)
        
        if commit and self.cleaned_data.get('question_type') == 'multiple_choice':
            # Delete existing choices if editing
            if question.pk:
                question.choices.all().delete()
            
            # Create new choices
            choices = []
            for i in range(1, 7):
                choice_text = self.cleaned_data.get(f'choice_{i}', '').strip()
                if choice_text:
                    choices.append(choice_text)
            
            correct_choice_num = int(self.cleaned_data.get('correct_choice', '1'))
            
            for i, choice_text in enumerate(choices, 1):
                QuizChoice.objects.create(
                    question=question,
                    choice_text=choice_text,
                    is_correct=(i == correct_choice_num),
                    order=i
                )
        
        return question