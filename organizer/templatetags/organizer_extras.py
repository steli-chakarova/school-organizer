from django import template
from django.utils.safestring import mark_safe
from django.utils.html import escape
import re

register = template.Library()

@register.filter
def lookup(dictionary, key):
    """Look up a key in a dictionary"""
    if isinstance(dictionary, dict):
        return dictionary.get(key, [])
    return []

@register.filter
def get_item(dictionary, key):
    """Get an item from a dictionary"""
    if isinstance(dictionary, dict):
        return dictionary.get(key)
    return None

@register.filter
def render_rich_text(content):
    """Safely render rich text content with HTML formatting"""
    if not content:
        return ""
    
    # Allow safe HTML tags for rich text formatting
    allowed_tags = [
        'p', 'br', 'strong', 'b', 'em', 'i', 'u', 's', 'strike',
        'h1', 'h2', 'h3', 'h4', 'h5', 'h6',
        'ul', 'ol', 'li',
        'table', 'thead', 'tbody', 'tr', 'th', 'td',
        'blockquote', 'div', 'span'
    ]
    
    allowed_attributes = [
        'style', 'class', 'id'
    ]
    
    # Clean and escape the content
    content = escape(content)
    
    # Allow specific HTML tags by unescaping them
    for tag in allowed_tags:
        # Unescape opening tags
        content = re.sub(rf'&lt;{tag}([^&]*?)&gt;', f'<{tag}\\1>', content)
        # Unescape closing tags
        content = re.sub(rf'&lt;/{tag}&gt;', f'</{tag}>', content)
    
    # Allow specific attributes
    for attr in allowed_attributes:
        content = re.sub(rf'({attr})=&quot;([^&]*?)&quot;', rf'{attr}="\2"', content)
        content = re.sub(rf'({attr})=&#x27;([^&]*?)&#x27;', rf'{attr}=\'\2\'', content)
    
    # Handle line breaks - convert \n to <br>
    content = content.replace('\\n', '<br>')
    
    return mark_safe(content)

@register.filter
def render_rich_text_safe(content):
    """Render rich text content as safe HTML (use with caution)"""
    if not content:
        return ""
    
    # This is for trusted content from the rich text editor
    # Mark as safe to render HTML
    return mark_safe(content)

@register.filter
def get_entry_data(entries, subject_schedule):
    """Get the specific entry data for a subject and position"""
    if not entries or not subject_schedule:
        return None
    
    subject_id = subject_schedule.subject.id if hasattr(subject_schedule, 'subject') else subject_schedule
    position = getattr(subject_schedule, 'entry_position', 0)
    
    for entry in entries:
        if entry.subject.id == subject_id and entry.position == position:
            return entry
    
    return None

@register.filter
def get_entry_field(entries, lookup_str):
    """Get a specific field from the matching entry
    Usage: {{ entries|get_entry_field:"subject_id:position:field_name" }}
    """
    if not entries or not lookup_str:
        return ""
    
    try:
        parts = lookup_str.split(':')
        if len(parts) != 3:
            return ""
        
        subject_id = int(parts[0])
        position = int(parts[1])
        field_name = parts[2]
        
        for entry in entries:
            if entry.subject.id == subject_id and entry.position == position:
                return getattr(entry, field_name, '') or ''
        
        return ""
    except (ValueError, AttributeError):
        return ""
