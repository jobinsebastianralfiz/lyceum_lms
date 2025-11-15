from django.shortcuts import render

# Create your views here.
from rest_framework import generics, status, permissions
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
from django.db import transaction
from .models import Notification, UserDevice
from .serializers import NotificationSerializer, DeviceRegistrationSerializer
from .push_service import PushNotificationService


class NotificationListView(generics.ListAPIView):
    """List user's notifications"""
    serializer_class = NotificationSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return Notification.objects.filter(user=self.request.user).order_by('-created_at')


@api_view(['POST'])
@permission_classes([permissions.AllowAny])  # Allow unauthenticated registration
def register_device(request):
    """Register device for push notifications (can be called before login)"""
    serializer = DeviceRegistrationSerializer(data=request.data)

    if serializer.is_valid():
        device_token = serializer.validated_data['device_token']
        device_type = serializer.validated_data['device_type']
        device_name = serializer.validated_data.get('device_name', '')

        try:
            with transaction.atomic():
                if request.user.is_authenticated:
                    # Check if there's an existing anonymous device with this token
                    anonymous_device = UserDevice.objects.filter(
                        device_token=device_token,
                        user=None,
                        is_active=True
                    ).first()

                    if anonymous_device:
                        # Link existing anonymous device to user
                        anonymous_device.user = request.user
                        anonymous_device.device_type = device_type
                        anonymous_device.device_name = device_name
                        anonymous_device.save()
                        device = anonymous_device
                        created = False
                        message = 'Device linked to user successfully (was anonymous)'
                    else:
                        # Create or update device for authenticated user
                        device, created = UserDevice.objects.update_or_create(
                            user=request.user,
                            device_token=device_token,
                            defaults={
                                'device_type': device_type,
                                'device_name': device_name,
                                'is_active': True
                            }
                        )
                        message = 'Device registered successfully for user'
                else:
                    # If user is not logged in, create anonymous device record
                    device, created = UserDevice.objects.update_or_create(
                        device_token=device_token,
                        user=None,  # Anonymous device
                        defaults={
                            'device_type': device_type,
                            'device_name': device_name,
                            'is_active': True
                        }
                    )
                    message = 'Device registered successfully (anonymous)'
        except Exception as e:
            return Response({
                'error': f'Failed to register device: {str(e)}'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        return Response({
            'success': True,
            'message': message,
            'device_id': device.id,
            'created': created,
            'authenticated': request.user.is_authenticated
        }, status=status.HTTP_201_CREATED if created else status.HTTP_200_OK)

    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def link_device_to_user(request):
    """Link an anonymous device to the authenticated user after login"""
    device_token = request.data.get('device_token')

    if not device_token:
        return Response({
            'error': 'device_token is required'
        }, status=status.HTTP_400_BAD_REQUEST)

    try:
        # Find anonymous device
        anonymous_device = UserDevice.objects.get(
            device_token=device_token,
            user=None,
            is_active=True
        )

        # Check if user already has this device registered
        existing_device = UserDevice.objects.filter(
            user=request.user,
            device_token=device_token
        ).first()

        if existing_device:
            # Delete the anonymous device, keep the user's device
            anonymous_device.delete()
            return Response({
                'success': True,
                'message': 'Device already linked to user'
            })
        else:
            # Link the anonymous device to the user
            anonymous_device.user = request.user
            anonymous_device.save()

            return Response({
                'success': True,
                'message': 'Device linked to user successfully'
            })

    except UserDevice.DoesNotExist:
        return Response({
            'error': 'Anonymous device not found'
        }, status=status.HTTP_404_NOT_FOUND)


@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def unregister_device(request):
    """Unregister user's device"""
    device_token = request.data.get('device_token')

    if not device_token:
        return Response({
            'error': 'device_token is required'
        }, status=status.HTTP_400_BAD_REQUEST)

    try:
        device = UserDevice.objects.get(
            user=request.user,
            device_token=device_token
        )
        device.is_active = False
        device.save()

        return Response({
            'success': True,
            'message': 'Device unregistered successfully'
        })
    except UserDevice.DoesNotExist:
        return Response({
            'error': 'Device not found'
        }, status=status.HTTP_404_NOT_FOUND)


@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def mark_notification_read(request, notification_id):
    """Mark notification as read"""
    try:
        notification = Notification.objects.get(
            id=notification_id,
            user=request.user
        )
        notification.read = True
        notification.save()

        return Response({
            'success': True,
            'message': 'Notification marked as read'
        })
    except Notification.DoesNotExist:
        return Response({
            'error': 'Notification not found'
        }, status=status.HTTP_404_NOT_FOUND)


@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def mark_all_read(request):
    """Mark all user notifications as read"""
    count = Notification.objects.filter(
        user=request.user,
        read=False
    ).update(read=True)

    return Response({
        'success': True,
        'message': f'Marked {count} notifications as read'
    })


@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def cleanup_user_devices(request):
    """Clean up duplicate or old devices for the authenticated user"""
    user = request.user

    # Get all user devices
    user_devices = UserDevice.objects.filter(user=user).order_by('-created_at')

    if user_devices.count() <= 1:
        return Response({
            'success': True,
            'message': 'No cleanup needed',
            'devices_count': user_devices.count()
        })

    # Keep the most recent device, deactivate others
    latest_device = user_devices.first()
    old_devices = user_devices.exclude(id=latest_device.id)

    deactivated_count = old_devices.update(is_active=False)

    return Response({
        'success': True,
        'message': f'Cleaned up {deactivated_count} old devices',
        'active_devices': 1,
        'latest_device_id': latest_device.id
    })


@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def device_status(request):
    """Get current user's device registration status"""
    user = request.user
    active_devices = UserDevice.objects.filter(user=user, is_active=True)

    return Response({
        'user_id': user.id,
        'user_name': user.name,
        'active_devices_count': active_devices.count(),
        'devices': [
            {
                'id': device.id,
                'device_type': device.device_type,
                'device_name': device.device_name,
                'created_at': device.created_at,
                'token_preview': device.device_token[:30] + '...'
            }
            for device in active_devices
        ]
    })


@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def test_notification(request):
    """Test push notification (development only)"""
    if not request.user.is_staff:
        return Response({
            'error': 'Admin access required'
        }, status=status.HTTP_403_FORBIDDEN)

    title = request.data.get('title', 'Test Notification')
    message = request.data.get('message', 'This is a test notification')

    success = PushNotificationService.send_to_user(
        request.user,
        title,
        message,
        {'type': 'test'}
    )

    return Response({
        'success': success,
        'message': 'Test notification sent' if success else 'Failed to send test notification'
    })
