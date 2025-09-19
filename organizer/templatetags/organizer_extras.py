from django import template

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
