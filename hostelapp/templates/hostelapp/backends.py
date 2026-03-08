# hostelapp/backends.py
from django.contrib.auth.backends import ModelBackend
from django.contrib.auth import get_user_model
from django.db.models import Q

User = get_user_model()


class RoleBasedAuthBackend(ModelBackend):
    def authenticate(self, request, username=None, password=None, **kwargs):
        # Get role from POST data
        role = request.POST.get('role') if request else kwargs.get('role')

        if not role:
            # If no role specified, use default authentication
            return super().authenticate(request, username=username, password=password, **kwargs)

        try:
            # Find user by username or email
            user = User.objects.get(Q(username=username) | Q(email=username))

            # Check password
            if user.check_password(password):
                # Check role based on user type
                if role == 'admin' and (user.is_staff or user.is_superuser):
                    return user
                elif role == 'student' and not user.is_staff and not user.is_superuser:
                    # Check if user has is_specialist attribute (if it exists)
                    if hasattr(user, 'is_specialist'):
                        if not user.is_specialist:
                            return user
                    else:
                        # If no is_specialist field, assume all non-staff are students
                        return user
                elif role == 'specialist' and hasattr(user, 'is_specialist') and user.is_specialist:
                    return user

        except User.DoesNotExist:
            return None

        return None