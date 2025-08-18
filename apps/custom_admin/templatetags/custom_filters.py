from django import template

register = template.Library()

@register.filter
def lookup(dictionary, key):
    """Get item from dictionary by key"""
    if isinstance(dictionary, dict):
        return dictionary.get(key, {'total': 0, 'completed': 0, 'incomplete': 0})
    return {'total': 0, 'completed': 0, 'incomplete': 0}