from django import template

register = template.Library()

@register.filter
def lookup(dictionary, key):
    """Get item from dictionary by key"""
    if isinstance(dictionary, dict):
        return dictionary.get(key, {'total': 0, 'completed': 0, 'incomplete': 0})
    return {'total': 0, 'completed': 0, 'incomplete': 0}

@register.filter
def mul(value, arg):
    """Multiply value by argument"""
    try:
        return float(value) * float(arg)
    except (ValueError, TypeError):
        return 0

@register.filter  
def div(value, arg):
    """Divide value by argument"""
    try:
        arg_float = float(arg)
        if arg_float == 0:
            return 0
        return float(value) / arg_float
    except (ValueError, TypeError):
        return 0

@register.filter
def percentage(value, total):
    """Calculate percentage of value from total"""
    try:
        total_float = float(total)
        if total_float == 0:
            return 0
        return round((float(value) / total_float) * 100, 1)
    except (ValueError, TypeError):
        return 0