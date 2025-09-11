from rest_framework import status, generics, permissions
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.exceptions import PermissionDenied
from rest_framework_simplejwt.views import TokenObtainPairView
from django.contrib.auth import get_user_model
from django.db import models
from drf_spectacular.utils import extend_schema, extend_schema_view, OpenApiExample
from drf_spectacular.openapi import OpenApiResponse

from .serializers import (
    CustomTokenObtainPairSerializer,
    UserRegistrationSerializer, 
    UserProfileSerializer,
    PasswordChangeSerializer,
    PasswordResetRequestSerializer,
    PasswordResetConfirmSerializer,
    TeamSerializer,
    TeamCreateSerializer,
    TeamMembershipSerializer,
    UserBasicSerializer
)
from .models import Team, TeamMembership, PasswordResetToken
from django.core.mail import send_mail
from django.conf import settings
from django.template.loader import render_to_string

User = get_user_model()

@extend_schema_view(
    post=extend_schema(
        summary="User Login",
        description="Authenticate user and obtain JWT tokens",
        request=CustomTokenObtainPairSerializer,
        responses={
            200: OpenApiResponse(
                description="Login successful",
                examples=[
                    OpenApiExample(
                        'Success Response',
                        value={
                            "access": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...",
                            "refresh": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9..."
                        }
                    )
                ]
            ),
            400: OpenApiResponse(
                description="Validation errors",
                examples=[
                    OpenApiExample(
                        'Invalid Email',
                        value={
                            "email": ["No account found with this email address. Please check your email or sign up."]
                        }
                    ),
                    OpenApiExample(
                        'Incorrect Password',
                        value={
                            "password": ["The password you entered is incorrect. Please try again."]
                        }
                    ),
                    OpenApiExample(
                        'Account Deactivated',
                        value={
                            "non_field_errors": ["This account has been deactivated. Please contact support for assistance."]
                        }
                    )
                ]
            )
        },
        tags=['Authentication']
    )
)
class CustomTokenObtainPairView(TokenObtainPairView):
    """
    Custom JWT token obtain view with user role information.
    """
    serializer_class = CustomTokenObtainPairSerializer

@extend_schema_view(
    post=extend_schema(
        summary="User Registration",
        description="Register a new student user account",
        request=UserRegistrationSerializer,
        responses={
            201: OpenApiResponse(
                description="User registered successfully",
                examples=[
                    OpenApiExample(
                        'Success Response',
                        value={
                            "message": "User registered successfully",
                            "user": {
                                "id": 1,
                                "email": "student@example.com",
                                "name": "John Doe",
                                "role": "student"
                            }
                        }
                    )
                ]
            ),
            400: OpenApiResponse(description="Validation errors")
        },
        tags=['Authentication']
    )
)
class UserRegistrationView(generics.CreateAPIView):
    """
    Register a new student user.
    """
    queryset = User.objects.all()
    serializer_class = UserRegistrationSerializer
    permission_classes = [permissions.AllowAny]
    
    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        
        return Response({
            'message': 'User registered successfully',
            'user': {
                'id': user.id,
                'email': user.email,
                'name': user.name,
                'role': user.role
            }
        }, status=status.HTTP_201_CREATED)

@extend_schema_view(
    get=extend_schema(
        summary="Get User Profile",
        description="Retrieve authenticated user's profile information",
        responses={
            200: UserProfileSerializer,
            401: OpenApiResponse(description="Authentication required")
        },
        tags=['User Profile']
    ),
    put=extend_schema(
        summary="Update User Profile",
        description="Update authenticated user's profile information",
        request=UserProfileSerializer,
        responses={
            200: UserProfileSerializer,
            400: OpenApiResponse(description="Validation errors"),
            401: OpenApiResponse(description="Authentication required")
        },
        tags=['User Profile']
    )
)
class UserProfileView(generics.RetrieveUpdateAPIView):
    """
    Retrieve and update user profile.
    """
    serializer_class = UserProfileSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_object(self):
        return self.request.user

@extend_schema_view(
    post=extend_schema(
        summary="Change Password",
        description="Change authenticated user's password",
        request=PasswordChangeSerializer,
        responses={
            200: OpenApiResponse(
                description="Password changed successfully",
                examples=[
                    OpenApiExample(
                        'Success Response',
                        value={"message": "Password changed successfully"}
                    )
                ]
            ),
            400: OpenApiResponse(description="Validation errors"),
            401: OpenApiResponse(description="Authentication required")
        },
        tags=['User Profile']
    )
)
class PasswordChangeView(APIView):
    """
    Change user password.
    """
    permission_classes = [permissions.IsAuthenticated]
    
    def post(self, request):
        serializer = PasswordChangeSerializer(data=request.data, context={'request': request})
        if serializer.is_valid():
            user = request.user
            user.set_password(serializer.validated_data['new_password'])
            user.save()
            return Response({'message': 'Password changed successfully'})
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

@extend_schema_view(
    post=extend_schema(
        summary="Password Reset Request",
        description="Send password reset email to user",
        request=PasswordResetRequestSerializer,
        responses={
            200: OpenApiResponse(
                description="Password reset email sent",
                examples=[
                    OpenApiExample(
                        'Success Response',
                        value={"message": "Password reset email sent successfully"}
                    )
                ]
            ),
            400: OpenApiResponse(description="User not found")
        },
        tags=['Authentication']
    )
)
class PasswordResetRequestView(APIView):
    """
    Request password reset email.
    """
    permission_classes = [permissions.AllowAny]
    
    def post(self, request):
        serializer = PasswordResetRequestSerializer(data=request.data)
        if serializer.is_valid():
            email = serializer.validated_data['email']
            try:
                user = User.objects.get(email=email)
                
                # Deactivate old tokens
                PasswordResetToken.objects.filter(user=user, is_used=False).update(is_used=True)
                
                # Create new token
                reset_token = PasswordResetToken.objects.create(user=user)
                
                # Send email
                reset_url = f"{request.build_absolute_uri('/')[:-1]}/auth/password-reset-confirm/{reset_token.token}/"
                
                try:
                    send_mail(
                        subject='Password Reset Request - CodeLearn LMS',
                        message=f'Click the following link to reset your password: {reset_url}',
                        from_email=settings.DEFAULT_FROM_EMAIL,
                        recipient_list=[email],
                        fail_silently=False,
                    )
                except Exception as e:
                    return Response({'error': 'Failed to send email'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
                
                return Response({'message': 'Password reset email sent successfully'})
            except User.DoesNotExist:
                # Return success even if user doesn't exist for security
                return Response({'message': 'Password reset email sent successfully'})
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

@extend_schema_view(
    post=extend_schema(
        summary="Password Reset Confirm",
        description="Confirm password reset with token and set new password",
        request=PasswordResetConfirmSerializer,
        responses={
            200: OpenApiResponse(
                description="Password reset successful",
                examples=[
                    OpenApiExample(
                        'Success Response',
                        value={"message": "Password reset successful"}
                    )
                ]
            ),
            400: OpenApiResponse(description="Invalid token or validation errors")
        },
        tags=['Authentication']
    )
)
class PasswordResetConfirmView(APIView):
    """
    Confirm password reset with token.
    """
    permission_classes = [permissions.AllowAny]
    
    def post(self, request, token):
        try:
            reset_token = PasswordResetToken.objects.get(token=token)
            
            if not reset_token.is_valid():
                return Response({'error': 'Invalid or expired token'}, status=status.HTTP_400_BAD_REQUEST)
            
            serializer = PasswordResetConfirmSerializer(data=request.data)
            if serializer.is_valid():
                # Update password
                user = reset_token.user
                user.set_password(serializer.validated_data['new_password'])
                user.save()
                
                # Mark token as used
                reset_token.is_used = True
                reset_token.save()
                
                return Response({'message': 'Password reset successful'})
            
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
            
        except PasswordResetToken.DoesNotExist:
            return Response({'error': 'Invalid token'}, status=status.HTTP_400_BAD_REQUEST)

# Team Management Views

@extend_schema_view(
    get=extend_schema(
        summary="List teams",
        description="Get list of teams with member information",
        responses={200: TeamSerializer(many=True)},
        tags=['Student - Teams']
    ),
    post=extend_schema(
        summary="Create team",
        description="Create a new team and optionally add members",
        request=TeamCreateSerializer,
        responses={
            201: TeamSerializer,
            400: OpenApiResponse(description="Validation errors")
        },
        examples=[
            OpenApiExample(
                'Create Team Request',
                value={
                    "name": "Python Developers",
                    "description": "Team for Python web development course",
                    "team_leader": 2,
                    "max_members": 5,
                    "member_ids": [2, 3, 4]
                }
            )
        ],
        tags=['Student - Teams']
    )
)
class TeamListCreateView(generics.ListCreateAPIView):
    """
    List all teams or create a new team.
    """
    serializer_class = TeamSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        user = self.request.user
        if user.role == 'admin':
            return Team.objects.all().prefetch_related('memberships__user')
        else:
            # Students can see teams they're part of or created
            return Team.objects.filter(
                models.Q(memberships__user=user) | models.Q(created_by=user)
            ).distinct().prefetch_related('memberships__user')
    
    def get_serializer_class(self):
        if self.request.method == 'POST':
            return TeamCreateSerializer
        return TeamSerializer

@extend_schema_view(
    get=extend_schema(
        summary="Get team details",
        description="Get detailed information about a specific team",
        responses={
            200: TeamSerializer,
            404: OpenApiResponse(description="Team not found")
        },
        tags=['Student - Teams']
    ),
    put=extend_schema(
        summary="Update team",
        description="Update team information",
        request=TeamSerializer,
        responses={
            200: TeamSerializer,
            403: OpenApiResponse(description="Permission denied"),
            404: OpenApiResponse(description="Team not found")
        },
        tags=['Student - Teams']
    ),
    delete=extend_schema(
        summary="Delete team",
        description="Delete a team (only team creator or admin)",
        responses={
            204: OpenApiResponse(description="Team deleted"),
            403: OpenApiResponse(description="Permission denied"),
            404: OpenApiResponse(description="Team not found")
        },
        tags=['Student - Teams']
    )
)
class TeamDetailView(generics.RetrieveUpdateDestroyAPIView):
    """
    Retrieve, update or delete a team.
    """
    queryset = Team.objects.all().prefetch_related('memberships__user')
    serializer_class = TeamSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_object(self):
        team = super().get_object()
        user = self.request.user
        
        # Check permissions
        if user.role != 'admin' and team.created_by != user:
            # Allow team members to view, but not modify
            if self.request.method in ['PUT', 'PATCH', 'DELETE']:
                if not team.memberships.filter(user=user, is_active=True).exists():
                    raise PermissionDenied("You don't have permission to modify this team")
        
        return team

@extend_schema_view(
    post=extend_schema(
        summary="Join team",
        description="Join an existing team",
        responses={
            200: OpenApiResponse(
                description="Successfully joined team",
                examples=[
                    OpenApiExample(
                        'Success Response',
                        value={"message": "Successfully joined team"}
                    )
                ]
            ),
            400: OpenApiResponse(description="Team is full or user already member"),
            404: OpenApiResponse(description="Team not found")
        },
        tags=['Student - Teams']
    )
)
class JoinTeamView(APIView):
    """
    Allow students to join a team.
    """
    permission_classes = [permissions.IsAuthenticated]
    
    def post(self, request, team_id):
        try:
            team = Team.objects.get(id=team_id, is_active=True)
        except Team.DoesNotExist:
            return Response({'error': 'Team not found'}, status=status.HTTP_404_NOT_FOUND)
        
        user = request.user
        
        # Check if user is already a member
        if team.memberships.filter(user=user, is_active=True).exists():
            return Response({'error': 'You are already a member of this team'}, status=status.HTTP_400_BAD_REQUEST)
        
        # Check if team is full
        if team.is_full:
            return Response({'error': 'Team is full'}, status=status.HTTP_400_BAD_REQUEST)
        
        # Add user to team
        TeamMembership.objects.create(team=team, user=user, role='member')
        
        return Response({'message': 'Successfully joined team'})

@extend_schema_view(
    post=extend_schema(
        summary="Leave team",
        description="Leave a team",
        responses={
            200: OpenApiResponse(
                description="Successfully left team",
                examples=[
                    OpenApiExample(
                        'Success Response',
                        value={"message": "Successfully left team"}
                    )
                ]
            ),
            400: OpenApiResponse(description="Not a member of this team"),
            404: OpenApiResponse(description="Team not found")
        },
        tags=['Student - Teams']
    )
)
class LeaveTeamView(APIView):
    """
    Allow students to leave a team.
    """
    permission_classes = [permissions.IsAuthenticated]
    
    def post(self, request, team_id):
        try:
            team = Team.objects.get(id=team_id)
        except Team.DoesNotExist:
            return Response({'error': 'Team not found'}, status=status.HTTP_404_NOT_FOUND)
        
        user = request.user
        
        try:
            membership = team.memberships.get(user=user, is_active=True)
            membership.is_active = False
            membership.save()
            return Response({'message': 'Successfully left team'})
        except TeamMembership.DoesNotExist:
            return Response({'error': 'You are not a member of this team'}, status=status.HTTP_400_BAD_REQUEST)

@extend_schema_view(
    get=extend_schema(
        summary="My teams",
        description="Get teams that the authenticated user is a member of",
        responses={200: TeamSerializer(many=True)},
        tags=['Student - Teams']
    )
)
class MyTeamsView(generics.ListAPIView):
    """
    List teams that the authenticated user is a member of.
    """
    serializer_class = TeamSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        return Team.objects.filter(
            memberships__user=self.request.user,
            memberships__is_active=True
        ).prefetch_related('memberships__user')

@extend_schema_view(
    delete=extend_schema(
        summary="Delete User Account",
        description="Delete the authenticated user's account including all enrollments and user data. Payment information is preserved.",
        responses={
            200: OpenApiResponse(
                description="Account deleted successfully",
                examples=[
                    OpenApiExample(
                        'Success Response',
                        value={"message": "Account deleted successfully"}
                    )
                ]
            ),
            401: OpenApiResponse(description="Authentication required")
        },
        tags=['User Profile']
    )
)
class DeleteAccountView(APIView):
    """
    Delete user account and all related data except payment information.
    """
    permission_classes = [permissions.IsAuthenticated]
    
    def delete(self, request):
        from django.db import transaction
        from rest_framework_simplejwt.tokens import RefreshToken
        from apps.payments.models import Enrollment
        from apps.courses.models import (
            StudentProgress, ModuleProgress, QuizAttempt, 
            AssignmentSubmission, StudentAnalytics, ProgressAlert, MentorSession
        )
        
        user = request.user
        
        try:
            with transaction.atomic():
                # Delete enrollments (but preserve payments)
                Enrollment.objects.filter(user=user).delete()
                
                # Delete student progress and course-related data
                StudentProgress.objects.filter(user=user).delete()
                ModuleProgress.objects.filter(student=user).delete()
                QuizAttempt.objects.filter(student=user).delete()
                AssignmentSubmission.objects.filter(student=user).delete()
                
                # Delete analytics and alerts
                if hasattr(user, 'analytics'):
                    user.analytics.delete()
                ProgressAlert.objects.filter(student=user).delete()
                
                # Delete mentor session records (as student)
                MentorSession.objects.filter(student=user).delete()
                
                # Delete team memberships
                TeamMembership.objects.filter(user=user).delete()
                
                # Delete teams created by user (if no other members)
                user_teams = Team.objects.filter(created_by=user)
                for team in user_teams:
                    if not team.memberships.filter(is_active=True).exists():
                        team.delete()
                    else:
                        # Transfer ownership to another active member
                        new_leader = team.memberships.filter(is_active=True).first()
                        if new_leader:
                            team.created_by = new_leader.user
                            team.team_leader = new_leader.user
                            team.save()
                
                # Delete password reset tokens
                PasswordResetToken.objects.filter(user=user).delete()
                
                # Get refresh token and blacklist it
                try:
                    refresh = RefreshToken.for_user(user)
                    refresh.blacklist()
                except Exception:
                    pass
                
                # Delete user account
                user.delete()
                
            return Response({'message': 'Account deleted successfully'}, status=status.HTTP_200_OK)
            
        except Exception as e:
            return Response({'error': 'Failed to delete account'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
