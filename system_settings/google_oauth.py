"""
Google OAuth 2.0 Flow Handler for Google Workspace Integration
"""
from google_auth_oauthlib.flow import Flow
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from django.conf import settings
from django.urls import reverse
from datetime import datetime, timedelta
from .models import GoogleWorkspaceIntegration
import os


# Google OAuth Scopes required for Calendar and Meet
GOOGLE_SCOPES = [
    'https://www.googleapis.com/auth/calendar.events',
    'https://www.googleapis.com/auth/calendar',
    'openid',
    'https://www.googleapis.com/auth/userinfo.email',
    'https://www.googleapis.com/auth/userinfo.profile',
]


class GoogleOAuthService:
    """Handle Google OAuth flow and token management"""

    def __init__(self, request=None):
        self.request = request
        self.client_config = self._get_client_config()

    def _get_client_config(self):
        """Get OAuth client configuration from settings"""
        from .utils import get_setting

        client_id = get_setting('GOOGLE_CLIENT_ID')
        client_secret = get_setting('GOOGLE_CLIENT_SECRET')

        if not client_id or not client_secret:
            raise ValueError(
                "Google OAuth credentials not configured. "
                "Please add GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET in system settings."
            )

        return {
            "web": {
                "client_id": client_id,
                "client_secret": client_secret,
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://oauth2.googleapis.com/token",
                "redirect_uris": [self._get_redirect_uri()],
            }
        }

    def _get_redirect_uri(self):
        """Build OAuth redirect URI"""
        if self.request:
            scheme = 'https' if self.request.is_secure() else 'http'
            host = self.request.get_host()
            path = reverse('custom_admin:google_oauth_callback')
            return f"{scheme}://{host}{path}"
        else:
            # Fallback for when request is not available
            from .utils import get_setting
            base_url = get_setting('GOOGLE_OAUTH_REDIRECT_BASE_URL', default='http://localhost:8000')
            path = reverse('custom_admin:google_oauth_callback')
            return f"{base_url}{path}"

    def get_authorization_url(self, state=None):
        """
        Generate authorization URL for OAuth flow
        Returns: (authorization_url, state)
        """
        flow = Flow.from_client_config(
            self.client_config,
            scopes=GOOGLE_SCOPES,
            redirect_uri=self._get_redirect_uri()
        )

        authorization_url, state = flow.authorization_url(
            access_type='offline',
            include_granted_scopes='true',
            prompt='consent'  # Force consent to get refresh token
        )

        return authorization_url, state

    def handle_callback(self, authorization_response, state):
        """
        Handle OAuth callback and exchange code for tokens
        Returns: credentials dict
        """
        flow = Flow.from_client_config(
            self.client_config,
            scopes=GOOGLE_SCOPES,
            state=state,
            redirect_uri=self._get_redirect_uri()
        )

        flow.fetch_token(authorization_response=authorization_response)
        credentials = flow.credentials

        # Get user info
        user_info = self._get_user_info(credentials)

        return {
            'access_token': credentials.token,
            'refresh_token': credentials.refresh_token,
            'token_expires_at': credentials.expiry,
            'scopes': credentials.scopes,
            'email': user_info.get('email'),
        }

    def _get_user_info(self, credentials):
        """Get user information from Google"""
        service = build('oauth2', 'v2', credentials=credentials)
        user_info = service.userinfo().get().execute()
        return user_info

    def save_credentials(self, user, credentials_dict):
        """Save or update Google credentials for user"""
        integration, created = GoogleWorkspaceIntegration.objects.update_or_create(
            admin_user=user,
            defaults={
                'google_email': credentials_dict['email'],
                'access_token': credentials_dict['access_token'],
                'refresh_token': credentials_dict['refresh_token'],
                'token_expires_at': credentials_dict['token_expires_at'],
                'scopes': credentials_dict['scopes'],
                'is_active': True,
            }
        )
        return integration

    def get_credentials_for_user(self, user):
        """
        Get Google credentials for user and refresh if expired
        Returns: Credentials object or None
        """
        try:
            integration = GoogleWorkspaceIntegration.objects.get(
                admin_user=user,
                is_active=True
            )
        except GoogleWorkspaceIntegration.DoesNotExist:
            return None

        # Check if token is expired
        if integration.is_token_expired():
            # Refresh the token
            credentials = self._refresh_token(integration)
            if not credentials:
                return None
        else:
            credentials = Credentials(
                token=integration.access_token,
                refresh_token=integration.refresh_token,
                token_uri=self.client_config['web']['token_uri'],
                client_id=self.client_config['web']['client_id'],
                client_secret=self.client_config['web']['client_secret'],
                scopes=integration.scopes
            )

        # Mark as used
        integration.mark_used()

        return credentials

    def _refresh_token(self, integration):
        """Refresh expired access token"""
        try:
            credentials = Credentials(
                token=integration.access_token,
                refresh_token=integration.refresh_token,
                token_uri=self.client_config['web']['token_uri'],
                client_id=self.client_config['web']['client_id'],
                client_secret=self.client_config['web']['client_secret'],
                scopes=integration.scopes
            )

            # Refresh the token
            credentials.refresh(Request())

            # Update database
            integration.access_token = credentials.token
            integration.token_expires_at = credentials.expiry
            integration.last_refreshed = datetime.now()
            integration.save(update_fields=['access_token', 'token_expires_at', 'last_refreshed'])

            return credentials
        except Exception as e:
            print(f"Error refreshing token: {e}")
            integration.is_active = False
            integration.save(update_fields=['is_active'])
            return None

    def disconnect(self, user):
        """Disconnect Google Workspace integration"""
        try:
            integration = GoogleWorkspaceIntegration.objects.get(admin_user=user)
            integration.is_active = False
            integration.save(update_fields=['is_active'])
            return True
        except GoogleWorkspaceIntegration.DoesNotExist:
            return False

    def test_connection(self, user):
        """Test if Google Calendar API is accessible"""
        credentials = self.get_credentials_for_user(user)
        if not credentials:
            return False, "No valid credentials found"

        try:
            service = build('calendar', 'v3', credentials=credentials)
            # Try to get calendar list
            calendars = service.calendarList().list(maxResults=1).execute()
            return True, "Connection successful"
        except Exception as e:
            return False, f"Connection failed: {str(e)}"
