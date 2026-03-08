from django.contrib import admin
from django.contrib.auth.models import User
from django.contrib.auth.admin import UserAdmin
from .models import UserProfile, Complaint, ComplaintUpdate


# Inline for UserProfile in User admin
class UserProfileInline(admin.StackedInline):
    model = UserProfile
    can_delete = False
    verbose_name_plural = 'Profile'


# Extend User Admin
class CustomUserAdmin(UserAdmin):
    inlines = [UserProfileInline]
    list_display = ('username', 'email', 'first_name', 'last_name', 'get_user_type', 'is_staff')
    list_select_related = ('profile',)

    def get_user_type(self, instance):
        return instance.profile.user_type if hasattr(instance, 'profile') else 'No profile'

    get_user_type.short_description = 'User Type'

    def get_queryset(self, request):
        return super().get_queryset(request).select_related('profile')


# Register Complaint model
@admin.register(Complaint)
class ComplaintAdmin(admin.ModelAdmin):
    list_display = ('id', 'title', 'student', 'assigned_to', 'status', 'priority', 'created_at')
    list_filter = ('status', 'priority', 'created_at')
    search_fields = ('title', 'description', 'student__username', 'assigned_to__username')
    readonly_fields = ('created_at', 'updated_at', 'completed_at')
    fieldsets = (
        ('Basic Information', {
            'fields': ('title', 'description', 'student', 'priority')
        }),
        ('Assignment', {
            'fields': ('assigned_to', 'status')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at', 'completed_at'),
            'classes': ('collapse',)
        }),
    )

    def save_model(self, request, obj, form, change):
        if not change:  # If creating new complaint
            obj.student = request.user if request.user.profile.user_type == 'student' else obj.student
        super().save_model(request, obj, form, change)


# Register ComplaintUpdate model
@admin.register(ComplaintUpdate)
class ComplaintUpdateAdmin(admin.ModelAdmin):
    list_display = ('complaint', 'user', 'status_change', 'created_at')
    list_filter = ('status_change', 'created_at')
    search_fields = ('complaint__title', 'user__username', 'message')
    readonly_fields = ('created_at',)


# Re-register User admin
admin.site.unregister(User)
admin.site.register(User, CustomUserAdmin)


# Optional: Create separate admins for different user types if needed
class StudentFilter(admin.SimpleListFilter):
    title = 'user type'
    parameter_name = 'user_type'

    def lookups(self, request, model_admin):
        return (
            ('students', 'Students'),
            ('professionals', 'Professionals'),
            ('admins', 'Admins'),
        )

    def queryset(self, request, queryset):
        if self.value() == 'students':
            return queryset.filter(profile__user_type='student')
        if self.value() == 'professionals':
            return queryset.filter(profile__user_type='professional')
        if self.value() == 'admins':
            return queryset.filter(profile__user_type='admin')
        return queryset


# You can also create a proxy model admin for students
class StudentUser(User):
    class Meta:
        proxy = True
        verbose_name = 'Student'
        verbose_name_plural = 'Students'


@admin.register(StudentUser)
class StudentUserAdmin(UserAdmin):
    def get_queryset(self, request):
        return super().get_queryset(request).filter(profile__user_type='student')

    list_display = ('username', 'email', 'first_name', 'last_name', 'get_room_number')

    def get_room_number(self, instance):
        return instance.profile.room_number if hasattr(instance, 'profile') else '-'

    get_room_number.short_description = 'Room Number'


# Proxy model for professionals
class ProfessionalUser(User):
    class Meta:
        proxy = True
        verbose_name = 'Professional'
        verbose_name_plural = 'Professionals'


@admin.register(ProfessionalUser)
class ProfessionalUserAdmin(UserAdmin):
    def get_queryset(self, request):
        return super().get_queryset(request).filter(profile__user_type='professional')

    list_display = ('username', 'email', 'first_name', 'last_name', 'get_specialization')

    def get_specialization(self, instance):
        return instance.profile.specialization if hasattr(instance, 'profile') else '-'

    get_specialization.short_description = 'Specialization'

