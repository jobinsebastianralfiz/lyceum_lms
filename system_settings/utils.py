"""
Utility functions for reading and writing system settings
"""
import os
from typing import Optional, Any
from django.core.cache import cache


def get_setting(key: str, default: Optional[Any] = None, use_cache: bool = True) -> Any:
    """
    Get a system setting value from database (with fallback to env variable)
    """
    cache_key = f"system_setting_{key}"

    if use_cache:
        cached_value = cache.get(cache_key)
        if cached_value is not None:
            return cached_value

    try:
        from .models import SystemSetting
        setting = SystemSetting.objects.filter(key=key, is_active=True).first()

        if setting:
            value = setting.value
            if use_cache:
                cache.set(cache_key, value, 300)
            return value
    except Exception as e:
        print(f"Error getting setting {key}: {e}")

    env_value = os.getenv(key)
    if env_value is not None:
        return env_value

    return default


def get_razorpay_key_id():
    return get_setting('RAZORPAY_KEY_ID')


def get_razorpay_key_secret():
    return get_setting('RAZORPAY_KEY_SECRET')
