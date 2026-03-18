from django.shortcuts import redirect
from django.contrib import messages
from functools import wraps


def is_admin(user):
    """Check if user is admin"""
    return user.is_authenticated and hasattr(user, 'profile') and user.profile.user_type == 'admin'


def is_specialist(user):
    """Check if user is specialist"""
    return user.is_authenticated and hasattr(user, 'profile') and user.profile.user_type == 'specialist'


def is_student(user):
    """Check if user is student"""
    return user.is_authenticated and hasattr(user, 'profile') and user.profile.user_type == 'student'


def admin_required(view_func):
    """Decorator to require admin access"""

    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        if not request.user.is_authenticated:
            messages.error(request, 'Please login to access this page.')
            return redirect('hostelapp:login')

        if not hasattr(request.user, 'profile') or request.user.profile.user_type != 'admin':
            messages.error(request, 'You do not have permission to access this page.')
            return redirect('hostelapp:dashboard')

        return view_func(request, *args, **kwargs)

    return _wrapped_view


def specialist_required(view_func):
    """Decorator to require specialist access"""

    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        if not request.user.is_authenticated:
            messages.error(request, 'Please login to access this page.')
            return redirect('hostelapp:login')

        if not hasattr(request.user, 'profile') or request.user.profile.user_type not in ['specialist', 'admin']:
            messages.error(request, 'You do not have permission to access this page.')
            return redirect('hostelapp:dashboard')

        return view_func(request, *args, **kwargs)

    return _wrapped_view


def student_required(view_func):
    """Decorator to require student access"""

    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        if not request.user.is_authenticated:
            messages.error(request, 'Please login to access this page.')
            return redirect('hostelapp:login')

        if not hasattr(request.user, 'profile') or request.user.profile.user_type not in ['student', 'admin']:
            messages.error(request, 'You do not have permission to access this page.')
            return redirect('hostelapp:dashboard')

        return view_func(request, *args, **kwargs)

    return _wrapped_view