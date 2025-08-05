from django import forms
from django.contrib.auth.forms import UserCreationForm, UserChangeForm
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from apps.users.models import User, Team, TeamMembership
from apps.youtube_integration.models import YouTubeChannelConfig, YouTubeVideo
from apps.payments.models import Enrollment, InstallmentPlan, Payment
from apps.courses.models import Course

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
        help_text='Course to enroll the student in'
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
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'step': '0.01',
            'placeholder': 'Enter total amount'
        }),
        help_text='Total enrollment amount including tax'
    )
    
    tax_amount = forms.DecimalField(
        max_digits=10,
        decimal_places=2,
        min_value=0,
        initial=0,
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'step': '0.01',
            'placeholder': 'Enter tax amount'
        }),
        help_text='Tax amount for this enrollment'
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
        # Set course price as default total_amount if creating new enrollment
        if not self.instance.pk and 'course' in self.data:
            try:
                course = Course.objects.get(pk=self.data['course'])
                if course.price:
                    self.fields['total_amount'].initial = course.price
            except (Course.DoesNotExist, ValueError):
                pass

    def clean(self):
        cleaned_data = super().clean()
        user = cleaned_data.get('user')
        course = cleaned_data.get('course')
        enrollment_type = cleaned_data.get('enrollment_type')
        team = cleaned_data.get('team')
        
        if user and course:
            # Check if user is already enrolled in this course
            existing_enrollment = Enrollment.objects.filter(
                user=user, 
                course=course
            ).exclude(pk=self.instance.pk if self.instance else None)
            
            if existing_enrollment.exists():
                raise ValidationError('This user is already enrolled in this course.')
        
        # Validate team enrollment
        if enrollment_type == 'team':
            if not team:
                raise ValidationError('Team is required for team enrollments.')
        elif enrollment_type != 'team' and team:
            # Clear team if not team enrollment
            cleaned_data['team'] = None
        
        # Validate tax amount doesn't exceed total amount
        total_amount = cleaned_data.get('total_amount', 0)
        tax_amount = cleaned_data.get('tax_amount', 0)
        if tax_amount > total_amount:
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
            has_installment_plan=False,
            payment_status__in=['pending', 'partial']
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
        cleaned_data = super().clean()
        enrollment = cleaned_data.get('enrollment')
        total_installments = cleaned_data.get('total_installments')
        installment_amount = cleaned_data.get('installment_amount')
        
        if enrollment and total_installments and installment_amount:
            # Calculate total plan amount
            total_plan_amount = total_installments * installment_amount
            
            # Check if total plan amount matches or is reasonable compared to enrollment amount
            enrollment_total = enrollment.total_amount or 0
            
            if total_plan_amount > enrollment_total * 1.1:  # Allow 10% margin for flexibility
                raise ValidationError(
                    f'Total installment amount (₹{total_plan_amount:.2f}) exceeds enrollment amount (₹{enrollment_total:.2f}) by more than 10%.'
                )
            
            if total_plan_amount < enrollment_total * 0.5:  # Must be at least 50% of enrollment
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