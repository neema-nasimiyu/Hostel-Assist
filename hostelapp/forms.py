from django import forms
from django.contrib.auth.models import User
from django.contrib.auth.forms import UserCreationForm as AuthUserCreationForm
from .models import Complaint, UserProfile


class ComplaintForm(forms.ModelForm):
    COMPLAINT_TYPES = [
        ('electrical', 'Electrical'),
        ('plumbing', 'Plumbing'),
        ('cleaning', 'Cleaning'),
        ('furniture', 'Furniture'),
        ('internet', 'Internet/WiFi'),
        ('security', 'Security'),
        ('other', 'Other'),
    ]

    PRIORITY_LEVELS = [
        ('low', 'Low'),
        ('medium', 'Medium'),
        ('high', 'High'),
        ('emergency', 'Emergency'),
    ]

    complaint_type = forms.ChoiceField(
        choices=COMPLAINT_TYPES,
        widget=forms.RadioSelect,
        required=True
    )

    class Meta:
        model = Complaint
        # ONLY include fields that exist in the database RIGHT NOW
        # Do NOT include hostel_name, room_number, phone_number, email yet
        fields = ['title', 'description', 'priority']
        # fields = ['title', 'description', 'complaint_type', 'priority',  # REMOVE THIS LINE FOR NOW
        #           'hostel_name', 'room_number', 'phone_number', 'email'] # REMOVE THIS LINE FOR NOW

        widgets = {
            'title': forms.TextInput(attrs={
                'placeholder': 'Brief title of your complaint',
                'class': 'form-control',
                'maxlength': '200'
            }),
            'description': forms.Textarea(attrs={
                'placeholder': 'Please describe your complaint in detail...',
                'maxlength': '500',
                'rows': 4,
                'class': 'form-control'
            }),
            'priority': forms.Select(attrs={'class': 'form-control'}),
            # Keep these commented out for now
            # 'hostel_name': forms.TextInput(attrs={
            #     'placeholder': 'e.g., Boys Hostel A',
            #     'class': 'form-control'
            # }),
            # 'room_number': forms.TextInput(attrs={
            #     'placeholder': 'e.g., A-101',
            #     'class': 'form-control'
            # }),
            # 'phone_number': forms.TextInput(attrs={
            #     'placeholder': 'e.g., 9876543210',
            #     'class': 'form-control'
            # }),
            # 'email': forms.EmailInput(attrs={
            #     'placeholder': 'your@email.com',
            #     'class': 'form-control'
            # }),
        }

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        self.fields['priority'].required = True

        # Keep this commented out for now
        # if self.user and hasattr(self.user, 'profile'):
        #     profile = self.user.profile
        #     if not self.initial.get('phone_number'):
        #         self.initial['phone_number'] = profile.phone_number
        #     if not self.initial.get('room_number'):
        #         self.initial['room_number'] = profile.room_number
        #     if not self.initial.get('email'):
        #         self.initial['email'] = self.user.email

# User Registration Form (using UserProfile)
class UserCreationForm(AuthUserCreationForm):
    USER_TYPES = (
        ('student', 'Student'),
        ('professional', 'Professional'),
        ('admin', 'Admin'),
    )

    user_type = forms.ChoiceField(choices=USER_TYPES, widget=forms.Select(attrs={'class': 'form-control'}))
    phone_number = forms.CharField(max_length=15, required=False,
                                   widget=forms.TextInput(
                                       attrs={'class': 'form-control', 'placeholder': 'Phone number'}))
    room_number = forms.CharField(max_length=10, required=False,
                                  widget=forms.TextInput(
                                      attrs={'class': 'form-control', 'placeholder': 'Room number (for students)'}))
    specialization = forms.CharField(max_length=100, required=False,
                                     widget=forms.TextInput(attrs={'class': 'form-control',
                                                                   'placeholder': 'Specialization (for professionals)'}))
    full_name = forms.CharField(max_length=200, required=True,
                                widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Full name'}))

    class Meta:
        model = User
        fields = ['username', 'email', 'password1', 'password2']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields:
            if field not in ['user_type', 'phone_number', 'room_number', 'specialization', 'full_name']:
                self.fields[field].widget.attrs['class'] = 'form-control'
                self.fields[field].widget.attrs['placeholder'] = field.capitalize()

    def save(self, commit=True):
        user = super().save(commit=True)

        # Split full name into first and last name
        full_name = self.cleaned_data.get('full_name', '')
        if full_name:
            name_parts = full_name.split()
            user.first_name = name_parts[0] if name_parts else ''
            user.last_name = ' '.join(name_parts[1:]) if len(name_parts) > 1 else ''
            user.save()

        user_type = self.cleaned_data['user_type']

        # Create or update profile
        profile, created = UserProfile.objects.get_or_create(user=user)
        profile.user_type = user_type
        profile.phone_number = self.cleaned_data.get('phone_number', '')

        if user_type == 'student':
            profile.room_number = self.cleaned_data.get('room_number', '')
            profile.specialization = ''  # Clear specialization for students
        elif user_type == 'professional':
            profile.specialization = self.cleaned_data.get('specialization', '')
            profile.room_number = ''  # Clear room number for professionals
        elif user_type == 'admin':
            profile.room_number = ''
            profile.specialization = ''

        profile.save()
        return user


#StudentRegistrationForm:

class StudentRegistrationForm(forms.Form):
    # Login Credentials
    username = forms.CharField(max_length=150,
                               widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Username'}))
    password = forms.CharField(widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': 'Password'}))
    confirm_password = forms.CharField(
        widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': 'Confirm password'}))
    email = forms.EmailField(widget=forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'Email'}))

    # Personal Information - Add missing fields
    full_name = forms.CharField(max_length=200,
                                widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Full name'}))
    student_id = forms.CharField(max_length=50,  # Add this field
                                 widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Student ID'}))
    phone_number = forms.CharField(max_length=15,
                                   widget=forms.TextInput(
                                       attrs={'class': 'form-control', 'placeholder': 'Phone number'}))
    room_number = forms.CharField(max_length=10,
                                  widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Room number'}))
    hostel_name = forms.CharField(max_length=100,  # Add this field
                                  widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Hostel name'}))
    department = forms.CharField(max_length=100,  # Add this field
                                 widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Department'}))

    def clean(self):
        cleaned_data = super().clean()
        password = cleaned_data.get('password')
        confirm_password = cleaned_data.get('confirm_password')

        if password and confirm_password and password != confirm_password:
            raise forms.ValidationError("Passwords do not match")

        return cleaned_data

    def clean_username(self):
        username = self.cleaned_data.get('username')
        if User.objects.filter(username=username).exists():
            raise forms.ValidationError("Username already exists")
        return username

    def clean_email(self):
        email = self.cleaned_data.get('email')
        if User.objects.filter(email=email).exists():
            raise forms.ValidationError("Email already exists")
        return email

    def save(self):
        # Create user account
        full_name = self.cleaned_data['full_name']
        user = User.objects.create_user(
            username=self.cleaned_data['username'],
            password=self.cleaned_data['password'],
            email=self.cleaned_data['email'],
            first_name=full_name.split()[0] if full_name else '',
            last_name=' '.join(full_name.split()[1:]) if len(full_name.split()) > 1 else ''
        )

        # Create user profile - You need to update your UserProfile model to include these fields
        profile = UserProfile.objects.create(
            user=user,
            user_type='student',
            phone_number=self.cleaned_data['phone_number'],
            room_number=self.cleaned_data['room_number'],

        )

        return user


# Professional Registration Form (Admin only - simplified)
class ProfessionalRegistrationForm(forms.Form):
    username = forms.CharField(max_length=150,
                               widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Username'}))
    password = forms.CharField(widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': 'Password'}))
    confirm_password = forms.CharField(
        widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': 'Confirm password'}))
    email = forms.EmailField(widget=forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'Email'}))
    full_name = forms.CharField(max_length=200,
                                widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Full name'}))
    phone_number = forms.CharField(max_length=15, widget=forms.TextInput(
        attrs={'class': 'form-control', 'placeholder': 'Phone number'}))
    specialization = forms.CharField(max_length=100, widget=forms.TextInput(
        attrs={'class': 'form-control', 'placeholder': 'Specialization (e.g., Plumber, Electrician)'}))

    def clean(self):
        cleaned_data = super().clean()
        password = cleaned_data.get('password')
        confirm_password = cleaned_data.get('confirm_password')

        if password and confirm_password and password != confirm_password:
            raise forms.ValidationError("Passwords do not match")

        return cleaned_data

    def clean_username(self):
        username = self.cleaned_data.get('username')
        if User.objects.filter(username=username).exists():
            raise forms.ValidationError("Username already exists")
        return username

    def clean_email(self):
        email = self.cleaned_data.get('email')
        if User.objects.filter(email=email).exists():
            raise forms.ValidationError("Email already exists")
        return email

    def save(self):
        # Create user account
        full_name = self.cleaned_data['full_name']
        user = User.objects.create_user(
            username=self.cleaned_data['username'],
            password=self.cleaned_data['password'],
            email=self.cleaned_data['email'],
            first_name=full_name.split()[0] if full_name else '',
            last_name=' '.join(full_name.split()[1:]) if len(full_name.split()) > 1 else ''
        )

        # Create user profile
        profile = UserProfile.objects.create(
            user=user,
            user_type='professional',
            phone_number=self.cleaned_data['phone_number'],
            specialization=self.cleaned_data['specialization']
        )

        return user


# Complaint Assignment Form
class ComplaintAssignForm(forms.Form):
    professional = forms.ModelChoiceField(
        queryset=User.objects.filter(profile__user_type='professional'),
        widget=forms.Select(attrs={'class': 'form-control'}),
        empty_label="Select a professional"
    )
    notes = forms.CharField(
        required=False,
        widget=forms.Textarea(
            attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Add assignment notes (optional)'}
        )
    )


# Bulk Upload Form
class BulkUploadForm(forms.Form):
    file = forms.FileField(
        label='Select CSV File',
        help_text='Please upload a CSV file with the required format.',
        widget=forms.FileInput(attrs={'class': 'form-control'})
    )