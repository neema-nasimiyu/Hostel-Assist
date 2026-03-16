from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone


class UserProfile(models.Model):
    USER_TYPES = (
        ('admin', 'Admin'),
        ('student', 'Student'),
        ('professional', 'Professional'),
    )

    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    user_type = models.CharField(max_length=20, choices=USER_TYPES, default='student')
    phone_number = models.CharField(max_length=15, blank=True)
    room_number = models.CharField(max_length=10, blank=True)  # For students
    specialization = models.CharField(max_length=100, blank=True)  # For professionals (electrician, plumber, etc.)
    hostel_name = models.CharField(max_length=50, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.username} - {self.user_type}"


class Complaint(models.Model):
    STATUS_CHOICES = (
        ('pending', 'Pending'),
        ('assigned', 'Assigned'),
        ('in_progress', 'In Progress'),
        ('completed', 'Completed'),
        ('rejected', 'Rejected'),
    )

    PRIORITY_CHOICES = (
        ('low', 'Low'),
        ('medium', 'Medium'),
        ('high', 'High'),
        ('emergency', 'Emergency'),
    )

    COMPLAINT_TYPES = (
        ('electrical', 'Electrical'),
        ('plumbing', 'Plumbing'),
        ('cleaning', 'Cleaning'),
        ('furniture', 'Furniture'),
        ('internet', 'Internet/WiFi'),
        ('security', 'Security'),
        ('other', 'Other'),
    )

    title = models.CharField(max_length=200)
    description = models.TextField()
    complaint_type = models.CharField(max_length=20, choices=COMPLAINT_TYPES, default='other')
    student = models.ForeignKey(User, on_delete=models.CASCADE, related_name='complaints')
    assigned_to = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True,
                                    related_name='assigned_complaints')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    priority = models.CharField(max_length=20, choices=PRIORITY_CHOICES, default='medium')

    # NEW FIELDS - Add these
    hostel_name = models.CharField(max_length=100, blank=True)
    room_number = models.CharField(max_length=10, blank=True)
    phone_number = models.CharField(max_length=15, blank=True)
    email = models.EmailField(blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"{self.title} - {self.student.username}"


class ComplaintUpdate(models.Model):
    complaint = models.ForeignKey(Complaint, on_delete=models.CASCADE, related_name='updates')
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    message = models.TextField()
    status_change = models.CharField(max_length=20, choices=Complaint.STATUS_CHOICES, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"Update on {self.complaint.title} by {self.user.username}"





