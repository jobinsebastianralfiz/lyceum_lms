from rest_framework import serializers
from .models import Notification, UserDevice


class NotificationSerializer(serializers.ModelSerializer):
    """Serializer for user notifications"""

    class Meta:
        model = Notification
        fields = [
            'id', 'notification_type', 'title', 'message', 'read', 'read_at',
            'metadata', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class DeviceRegistrationSerializer(serializers.Serializer):
    """Serializer for device registration"""
    device_token = serializers.CharField(max_length=500, required=True)
    device_type = serializers.ChoiceField(
        choices=[('ios', 'iOS'), ('android', 'Android'), ('web', 'Web')],
        required=True
    )
    device_name = serializers.CharField(max_length=100, required=False, allow_blank=True)

    def validate_device_token(self, value):
        if len(value) < 10:
            raise serializers.ValidationError("Invalid device token")
        return value


class UserDeviceSerializer(serializers.ModelSerializer):
    """Serializer for user devices"""

    class Meta:
        model = UserDevice
        fields = ['id', 'device_type', 'device_name', 'is_active', 'created_at']
        read_only_fields = ['id', 'created_at']