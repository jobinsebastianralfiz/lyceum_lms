from django.conf import settings


def cloudflare_turnstile(request):
    """Add Cloudflare Turnstile site key to template context"""
    return {
        'CLOUDFLARE_TURNSTILE_SITE_KEY': getattr(settings, 'CLOUDFLARE_TURNSTILE_SITE_KEY', ''),
    }


def feature_config(request):
    """
    Make feature configuration available in all templates.
    Cached for performance.
    """
    try:
        from apps.core.models import FeatureConfig
        features = FeatureConfig.get_features_dict()
    except Exception:
        # Fallback - all features enabled if model not ready
        features = {
            'online_courses': True,
            'live_sessions': True,
            'online_enrollment': True,
            'certificates': True,
            'tuition': True,
            'finance': True,
            'payments': True,
            'assessments': True,
            'notifications': True,
            'website_content': True,
            'youtube': True,
            'analytics': True,
        }

    return {'features': features}
