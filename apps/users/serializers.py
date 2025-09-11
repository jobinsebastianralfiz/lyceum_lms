from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from django.contrib.auth import authenticate
from django.contrib.auth.hashers import check_password
from drf_spectacular.utils import extend_schema_field
from .models import User, Team, TeamMembership

class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    """
    Custom JWT token serializer that includes user role and name in the token payload
    and provides specific error messages for failed authentication.
    """
    
    def validate(self, attrs):
        # Get email and password from the input
        email = attrs.get('email') or attrs.get('username')
        password = attrs.get('password')
        
        # Basic validation
        if not email:
            raise serializers.ValidationError({
                'email': ['Email address is required.']
            })
        
        if not password:
            raise serializers.ValidationError({
                'password': ['Password is required.']
            })
        
        # Normalize email
        email = email.lower().strip()
        
        # Check if user exists
        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            raise serializers.ValidationError({
                'email': ['No account found with this email address. Please check your email or sign up.']
            })
        
        # Check if user is active
        if not user.is_active:
            raise serializers.ValidationError({
                'non_field_errors': ['This account has been deactivated. Please contact support for assistance.']
            })
        
        # Check password
        if not check_password(password, user.password):
            raise serializers.ValidationError({
                'password': ['The password you entered is incorrect. Please try again.']
            })
        
        # If we get here, authentication should succeed
        # Ensure the parent class gets the right field
        attrs['username'] = email
        
        # Call parent validation (this will generate the tokens)
        try:
            data = super().validate(attrs)
            return data
        except Exception as e:
            # If something still goes wrong, provide a generic error
            raise serializers.ValidationError({
                'non_field_errors': ['Authentication failed. Please try again.']
            })
    
    @classmethod
    def get_token(cls, user):
        token = super().get_token(user)
        token['role'] = user.role
        token['name'] = user.name
        token['user_id'] = user.id
        return token

class UserRegistrationSerializer(serializers.ModelSerializer):
    """
    Serializer for user registration with validation.
    """
    password = serializers.CharField(write_only=True, min_length=8)
    password_confirm = serializers.CharField(write_only=True)
    
    class Meta:
        model = User
        fields = ['email', 'name', 'password', 'password_confirm', 'phone_number', 'address']
        extra_kwargs = {
            'email': {'required': True},
            'name': {'required': True}
        }
    
    def validate(self, attrs):
        if attrs['password'] != attrs['password_confirm']:
            raise serializers.ValidationError("Passwords don't match")
        return attrs
    
    def create(self, validated_data):
        validated_data.pop('password_confirm')
        password = validated_data.pop('password')
        user = User.objects.create_user(
            username=validated_data['email'],
            **validated_data
        )
        user.set_password(password)
        user.save()
        return user

class UserProfileSerializer(serializers.ModelSerializer):
    """
    Serializer for user profile information.
    """
    
    class Meta:
        model = User
        fields = ['id', 'email', 'name', 'role', 'phone_number', 'address', 'date_joined']
        read_only_fields = ['id', 'email', 'role', 'date_joined']

class UserBasicSerializer(serializers.ModelSerializer):
    """
    Basic user info for team members display
    """
    class Meta:
        model = User
        fields = ['id', 'name', 'email']

class TeamMembershipSerializer(serializers.ModelSerializer):
    """
    Serializer for team membership
    """
    user = UserBasicSerializer(read_only=True)
    user_id = serializers.IntegerField(write_only=True)
    
    class Meta:
        model = TeamMembership
        fields = ['id', 'user', 'user_id', 'role', 'joined_at', 'is_active']
        read_only_fields = ['id', 'joined_at']

class TeamSerializer(serializers.ModelSerializer):
    """
    Serializer for team management
    """
    members = TeamMembershipSerializer(source='memberships', many=True, read_only=True)
    member_count = serializers.ReadOnlyField()
    available_spots = serializers.ReadOnlyField()
    is_full = serializers.ReadOnlyField()
    team_leader_name = serializers.CharField(source='team_leader.name', read_only=True)
    created_by_name = serializers.CharField(source='created_by.name', read_only=True)
    
    class Meta:
        model = Team
        fields = [
            'id', 'name', 'description', 'team_leader', 'team_leader_name',
            'max_members', 'member_count', 'available_spots', 'is_full',
            'is_active', 'created_by', 'created_by_name', 'members', 'created_at'
        ]
        read_only_fields = ['id', 'created_by', 'created_at']

class TeamCreateSerializer(serializers.ModelSerializer):
    """
    Serializer for creating teams
    """
    member_ids = serializers.ListField(
        child=serializers.IntegerField(), 
        write_only=True, 
        required=False,
        help_text="List of user IDs to add as team members"
    )
    
    class Meta:
        model = Team
        fields = ['name', 'description', 'team_leader', 'max_members', 'member_ids']
    
    def create(self, validated_data):
        member_ids = validated_data.pop('member_ids', [])
        request = self.context.get('request')
        
        team = Team.objects.create(
            created_by=request.user,
            **validated_data
        )
        
        # Add members to team
        for user_id in member_ids:
            try:
                user = User.objects.get(id=user_id, role='student')
                TeamMembership.objects.create(
                    team=team,
                    user=user,
                    role='leader' if user == team.team_leader else 'member'
                )
            except User.DoesNotExist:
                continue
        
        return team

class PasswordChangeSerializer(serializers.Serializer):
    """
    Serializer for changing user password.
    """
    old_password = serializers.CharField(required=True)
    new_password = serializers.CharField(required=True, min_length=8)
    new_password_confirm = serializers.CharField(required=True)
    
    def validate(self, attrs):
        if attrs['new_password'] != attrs['new_password_confirm']:
            raise serializers.ValidationError("New passwords don't match")
        return attrs
    
    def validate_old_password(self, value):
        user = self.context['request'].user
        if not user.check_password(value):
            raise serializers.ValidationError("Old password is incorrect")
        return value

class PasswordResetRequestSerializer(serializers.Serializer):
    """
    Serializer for password reset request.
    """
    email = serializers.EmailField(required=True)
    
    def validate_email(self, value):
        # We don't validate if user exists for security reasons
        # The view will handle this logic
        return value

class PasswordResetConfirmSerializer(serializers.Serializer):
    """
    Serializer for password reset confirmation.
    """
    new_password = serializers.CharField(required=True, min_length=8)
    new_password_confirm = serializers.CharField(required=True)
    
    def validate(self, attrs):
        if attrs['new_password'] != attrs['new_password_confirm']:
            raise serializers.ValidationError("Passwords don't match")
        return attrs