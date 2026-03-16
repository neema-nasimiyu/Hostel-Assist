from django import template

register = template.Library()

@register.filter
def has_attr(obj, attr_name):
    """Check if an object has a specific attribute"""
    return hasattr(obj, attr_name)

@register.filter
def get_user_type(user):
    """Get user type from profile"""
    if hasattr(user, 'profile') and user.profile:
        return user.profile.user_type
    return None