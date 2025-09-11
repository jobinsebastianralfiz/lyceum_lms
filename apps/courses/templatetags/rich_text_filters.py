from django import template
from django.utils.safestring import mark_safe
import html
import re

register = template.Library()

@register.filter(name='clean_rich_text')
def clean_rich_text(value):
    """
    Clean and format rich text content from Quill editor
    """
    if not value:
        return ''
    
    # Decode HTML entities first
    cleaned = html.unescape(value)
    
    # Remove empty paragraphs and line breaks
    cleaned = re.sub(r'<p><br></p>', '', cleaned)
    cleaned = re.sub(r'<p>&nbsp;</p>', '', cleaned)
    cleaned = re.sub(r'<p>\s*</p>', '', cleaned)
    
    # Remove excessive whitespace
    cleaned = re.sub(r'\s+', ' ', cleaned)
    
    # Ensure proper paragraph spacing
    cleaned = re.sub(r'</p><p>', '</p>\n<p>', cleaned)
    
    return mark_safe(cleaned.strip())

@register.filter(name='safe_rich_text')
def safe_rich_text(value):
    """
    Safely render rich text content with basic cleaning
    """
    if not value:
        return ''
    
    # First clean the content
    cleaned = clean_rich_text(value)
    
    # Return as safe HTML
    return cleaned