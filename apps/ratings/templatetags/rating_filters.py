from django import template
from django.db.models import Avg

register = template.Library()


@register.filter
def avg_rating(course):
    """Calculate average rating for a course"""
    avg = course.ratings.filter(is_approved=True).aggregate(avg_rating=Avg('rating'))['avg_rating']
    return avg if avg is not None else 0


@register.filter
def rating_percentage(rating, max_rating=5):
    """Convert rating to percentage for star display"""
    if not rating:
        return 0
    return (rating / max_rating) * 100


@register.simple_tag
def get_star_display(rating):
    """Get star display for a rating"""
    if not rating:
        return "☆☆☆☆☆"
    
    full_stars = int(rating)
    half_star = 1 if (rating - full_stars) >= 0.5 else 0
    empty_stars = 5 - full_stars - half_star
    
    return "★" * full_stars + "☆" * (5 - full_stars)