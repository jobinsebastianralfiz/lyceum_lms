from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from django.contrib.auth import authenticate
from drf_spectacular.utils import extend_schema_field
from .models import User, Team, TeamMembership

class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    """
    Custom JWT token serializer that includes user role and name in the token payload.
    """
    
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
        if not User.objects.filter(email=value).exists():
            raise serializers.ValidationError("User with this email does not exist")
        return value