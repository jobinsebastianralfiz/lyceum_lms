from django.conf import settings
import logging
import json
import os
from typing import Optional, Dict, Any, List
from .models import UserDevice, Notification

logger = logging.getLogger(__name__)

# Initialize Firebase Admin SDK
FIREBASE_AVAILABLE = False
try:
    import firebase_admin
    from firebase_admin import credentials, messaging

    # Check if Firebase is already initialized
    if not firebase_admin._apps:
        if hasattr(settings, 'FIREBASE_CREDENTIALS_PATH') and settings.FIREBASE_CREDENTIALS_PATH:
            if os.path.exists(settings.FIREBASE_CREDENTIALS_PATH):
                cred = credentials.Certificate(settings.FIREBASE_CREDENTIALS_PATH)
                firebase_admin.initialize_app(cred)
                FIREBASE_AVAILABLE = True
                logger.info("Firebase Admin SDK initialized successfully")
            else:
                logger.warning(f"Firebase credentials file not found: {settings.FIREBASE_CREDENTIALS_PATH}")
        else:
            logger.warning("FIREBASE_CREDENTIALS_PATH not configured")
    else:
        FIREBASE_AVAILABLE = True
        logger.info("Firebase Admin SDK already initialized")

except ImportError:
    logger.warning("firebase-admin not installed. Push notifications will be logged only.")
except Exception as e:
    logger.warning(f"Firebase Admin SDK initialization failed: {e}")

# Fallback to legacy FCM if modern approach fails
LEGACY_FCM_AVAILABLE = False
if not FIREBASE_AVAILABLE:
    try:
        from pyfcm import FCMNotification
        server_key = getattr(settings, 'FCM_SERVER_KEY', None)
        if server_key and server_key != 'your-fcm-server-key-here':
            fcm = FCMNotification(server_key=server_key)  # Use server_key parameter instead of api_key
            LEGACY_FCM_AVAILABLE = True
            logger.info("Using legacy FCM with pyfcm")
        else:
            logger.warning("FCM_SERVER_KEY not configured properly")
    except ImportError:
        logger.warning("pyfcm not available")
    except Exception as e:
        logger.warning(f"Legacy FCM initialization failed: {e}")


class PushNotificationService:
    """Service for sending push notifications via FCM"""

    @staticmethod
    def send_to_user(user, title: str, message_body: str, data: Optional[Dict[str, Any]] = None) -> bool:
        """Send push notification to all user's devices"""
        if not user or not user.is_active:
            return False

        # Get user's active devices
        devices = UserDevice.objects.filter(user=user, is_active=True)
        if not devices.exists():
            logger.info(f"No active devices found for user {user.id}")
            return False

        device_tokens = [device.device_token for device in devices]
        if not device_tokens:
            return False

        # Prepare notification data
        notification_data = data or {}
        notification_data.update({
            'click_action': 'FLUTTER_NOTIFICATION_CLICK',
            'sound': 'default'
        })

        # Use modern Firebase Admin SDK if available
        if FIREBASE_AVAILABLE:
            return PushNotificationService._send_with_admin_sdk(
                device_tokens, title, message_body, notification_data, user.id
            )

        # Fallback to legacy FCM
        elif LEGACY_FCM_AVAILABLE:
            return PushNotificationService._send_with_legacy_fcm(
                device_tokens, title, message_body, notification_data, user.id, devices
            )

        # No FCM available - log only
        else:
            logger.info(f"PUSH NOTIFICATION (No FCM available)")
            logger.info(f"User: {user.name} ({user.id})")
            logger.info(f"Title: {title}")
            logger.info(f"Message: {message_body}")
            logger.info(f"Data: {json.dumps(notification_data, indent=2)}")
            logger.info(f"Devices: {len(device_tokens)}")
            return True

    @staticmethod
    def _send_with_admin_sdk(device_tokens: List[str], title: str, message_body: str,
                           data: Dict[str, Any], user_id: int) -> bool:
        """Send notifications using Firebase Admin SDK (modern approach)"""
        try:
            from firebase_admin import messaging

            # Create messages for each device token
            messages = []
            for token in device_tokens:
                message = messaging.Message(
                    notification=messaging.Notification(
                        title=title,
                        body=message_body,
                    ),
                    data={str(k): str(v) for k, v in data.items()},  # Convert all values to strings
                    token=token,
                    android=messaging.AndroidConfig(
                        notification=messaging.AndroidNotification(
                            click_action=data.get('click_action', 'FLUTTER_NOTIFICATION_CLICK'),
                            sound='default'
                        )
                    ),
                    apns=messaging.APNSConfig(
                        payload=messaging.APNSPayload(
                            aps=messaging.Aps(
                                sound='default',
                                category=data.get('click_action', 'FLUTTER_NOTIFICATION_CLICK')
                            )
                        )
                    )
                )
                messages.append(message)

            # Send batch of messages
            if len(messages) == 1:
                # Single message
                response = messaging.send(messages[0])
                logger.info(f"Push notification sent successfully to user {user_id}: {response}")
                return True
            else:
                # Batch send
                response = messaging.send_all(messages)
                success_count = response.success_count
                failure_count = response.failure_count

                logger.info(f"Push notification batch: {success_count} success, {failure_count} failures for user {user_id}")

                # Handle failures
                if failure_count > 0:
                    PushNotificationService._handle_admin_sdk_failures(response, device_tokens)

                return success_count > 0

        except Exception as e:
            logger.error(f"Error sending push notification with Admin SDK to user {user_id}: {str(e)}")
            return False

    @staticmethod
    def _send_with_legacy_fcm(device_tokens: List[str], title: str, message_body: str,
                            data: Dict[str, Any], user_id: int, devices) -> bool:
        """Send notifications using legacy pyfcm"""
        try:
            result = fcm.notify_multiple_devices(
                registration_ids=device_tokens,
                message_title=title,
                message_body=message_body,
                data_message=data
            )

            if result and result.get('success', 0) > 0:
                success_count = result.get('success', 0)
                logger.info(f"Push notification sent successfully to {success_count}/{len(device_tokens)} devices for user {user_id}")

                # Handle failed tokens
                if result.get('canonical_ids', 0) > 0 or result.get('failure', 0) > 0:
                    PushNotificationService._handle_legacy_failed_tokens(result, devices)

                return True
            else:
                logger.error(f"Failed to send push notification to user {user_id}: {result}")
                return False

        except Exception as e:
            logger.error(f"Error sending push notification with legacy FCM to user {user_id}: {str(e)}")
            return False

    @staticmethod
    def send_to_multiple_users(users, title: str, message: str, data: Optional[Dict[str, Any]] = None) -> Dict[str, bool]:
        """Send push notification to multiple users"""
        results = {}

        for user in users:
            try:
                success = PushNotificationService.send_to_user(user, title, message, data)
                results[user.id] = success
            except Exception as e:
                logger.error(f"Error sending notification to user {user.id}: {str(e)}")
                results[user.id] = False

        return results

    @staticmethod
    def _handle_admin_sdk_failures(response, device_tokens: List[str]):
        """Handle failed device tokens from Firebase Admin SDK"""
        try:
            for idx, result in enumerate(response.responses):
                if not result.success:
                    token = device_tokens[idx]
                    error_code = result.exception.code if result.exception else 'unknown'
                    logger.warning(f"Failed to send to token {token[:20]}...: {error_code}")

                    # Deactivate invalid tokens
                    if error_code in ['UNREGISTERED', 'INVALID_ARGUMENT']:
                        UserDevice.objects.filter(device_token=token).update(is_active=False)
                        logger.info(f"Deactivated invalid device token: {token[:20]}...")

        except Exception as e:
            logger.error(f"Error handling Admin SDK failures: {str(e)}")

    @staticmethod
    def _handle_legacy_failed_tokens(result: Dict[str, Any], devices: List[UserDevice]):
        """Handle failed/invalid device tokens from legacy FCM"""
        try:
            if result.get('failure', 0) > 0:
                logger.warning(f"Some device tokens failed: {result.get('failure', 0)} failures")

            if result.get('canonical_ids', 0) > 0:
                logger.info(f"Some device tokens need update: {result.get('canonical_ids', 0)} canonical IDs")

        except Exception as e:
            logger.error(f"Error handling legacy failed tokens: {str(e)}")


def send_session_notification(user, notification_type: str, session, extra_data: Optional[Dict[str, Any]] = None):
    """Send live session related notifications"""
    from apps.live_sessions.models import LiveSession

    if not isinstance(session, LiveSession):
        logger.error("Invalid session object provided")
        return False

    # Prepare notification content based on type
    title_map = {
        'session_assigned': f"New Session Assigned",
        'session_started': f"Session Started",
        'session_reminder': f"Session Reminder",
        'session_cancelled': f"Session Cancelled",
        'session_announcement': f"Session Update"
    }

    message_map = {
        'session_assigned': f"You've been assigned to '{session.title}' scheduled for {session.scheduled_date.strftime('%Y-%m-%d %H:%M')}",
        'session_started': f"'{session.title}' is now live! Tap to join.",
        'session_reminder': f"'{session.title}' starts in 15 minutes. Get ready!",
        'session_cancelled': f"'{session.title}' scheduled for {session.scheduled_date.strftime('%Y-%m-%d %H:%M')} has been cancelled.",
        'session_announcement': f"New announcement for '{session.title}'"
    }

    title = title_map.get(notification_type, "Session Update")
    message = message_map.get(notification_type, f"Update for session '{session.title}'")

    # Prepare notification data for mobile app
    notification_data = {
        'type': notification_type,
        'session_id': str(session.id),
        'session_title': session.title,
        'session_date': session.scheduled_date.isoformat(),
        'action': 'open_session' if notification_type == 'session_started' else 'view_sessions'
    }

    if extra_data:
        notification_data.update(extra_data)

    # Send push notification
    success = PushNotificationService.send_to_user(user, title, message, notification_data)

    # Create database notification record
    try:
        Notification.objects.create(
            user=user,
            notification_type=notification_type,
            title=title,
            message=message,
            push_sent=success,
            push_status='sent' if success else 'failed',
            metadata={
                'session_id': session.id,
                'session_title': session.title,
                **notification_data
            }
        )
    except Exception as e:
        logger.error(f"Error creating notification record: {str(e)}")

    return success