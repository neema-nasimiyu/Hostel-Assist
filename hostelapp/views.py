from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth import authenticate, login
from django.contrib.auth.models import User
from django.contrib import messages
from django.db.models import Count, Q
from django.utils import timezone
from django.http import HttpResponse
from django.core.paginator import Paginator
from datetime import datetime, timedelta
import csv
import io

# ReportLab imports for PDF
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter, A4
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch

# Import your models
from .models import UserProfile, Complaint, ComplaintUpdate
from .forms import ComplaintForm, UserCreationForm, ComplaintAssignForm

from django.shortcuts import render, redirect
from django.contrib import messages
from .forms import StudentRegistrationForm, ProfessionalRegistrationForm



# ==================== HELPER FUNCTIONS ====================
def is_admin(user):
    return user.is_authenticated and hasattr(user, 'profile') and user.profile.user_type == 'admin'


def is_student(user):
    return user.is_authenticated and hasattr(user, 'profile') and user.profile.user_type == 'student'


def is_professional(user):
    return user.is_authenticated and hasattr(user, 'profile') and user.profile.user_type == 'professional'


# ==================== AUTHENTICATION VIEWS ====================
def role_based_login(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        role = request.POST.get('role')

        user = authenticate(request, username=username, password=password)

        if user is not None:
            # Get or create user profile
            profile, created = UserProfile.objects.get_or_create(user=user)

            # Check role and redirect to appropriate dashboard
            if role == 'admin' and (user.is_staff or user.is_superuser):
                # Update profile user_type if needed
                if profile.user_type != 'admin':
                    profile.user_type = 'admin'
                    profile.save()
                login(request, user)
                messages.success(request, f'Welcome Admin {user.username}!')
                return redirect('hostelapp:admin_dashboard')

            elif role == 'student' and not user.is_staff and not user.is_superuser:
                # Check if user is a professional
                if profile.user_type == 'professional':
                    messages.error(request,
                                   'This account is registered as a Professional. Please login as Professional.')
                else:
                    # Update profile user_type if needed
                    if profile.user_type != 'student':
                        profile.user_type = 'student'
                        profile.save()
                    login(request, user)
                    messages.success(request, f'Welcome Student {user.username}!')
                    return redirect('hostelapp:student_dashboard')

            elif role == 'professional' and profile.user_type == 'professional':
                login(request, user)
                messages.success(request, f'Welcome Professional {user.username}!')
                return redirect('hostelapp:professional_dashboard')

            else:
                messages.error(request, f'Invalid role for this user. You cannot login as {role}.')
        else:
            messages.error(request, 'Invalid username or password.')

    return render(request, 'registration/login.html')


# ==================== DASHBOARD VIEWS ====================
@login_required
def dashboard(request):
    user = request.user

    # Redirect to role-specific dashboards
    if hasattr(user, 'profile'):
        if user.profile.user_type == 'admin':
            return redirect('hostelapp:admin_dashboard')
        elif user.profile.user_type == 'professional':
            return redirect('hostelapp:professional_dashboard')
        elif user.profile.user_type == 'student':
            return redirect('hostelapp:student_dashboard')

    # Default fallback
    return redirect('hostelapp:login')


@login_required
@user_passes_test(is_admin)
def admin_dashboard(request):
    """Admin dashboard view"""
    # Get counts
    total_complaints = Complaint.objects.count()
    pending_complaints = Complaint.objects.filter(status='pending').count()
    assigned_complaints = Complaint.objects.filter(status='assigned').count()
    in_progress_complaints = Complaint.objects.filter(status='in_progress').count()
    completed_complaints = Complaint.objects.filter(status='completed').count()

    # Get user counts
    total_students = UserProfile.objects.filter(user_type='student').count()
    total_professionals = UserProfile.objects.filter(user_type='professional').count()

    # Get recent complaints
    recent_complaints = Complaint.objects.all().order_by('-created_at')[:10]

    # Get professionals with their active tasks
    professionals = User.objects.filter(profile__user_type='professional')
    professional_data = []
    for prof in professionals:
        active_tasks = Complaint.objects.filter(
            assigned_to=prof,
            status__in=['assigned', 'in_progress']
        ).count()
        completed_tasks = Complaint.objects.filter(
            assigned_to=prof,
            status='completed'
        ).count()
        professional_data.append({
            'user': prof,
            'profile': prof.profile,
            'active_tasks': active_tasks,
            'completed_tasks': completed_tasks
        })

    # Get pending tasks (unassigned complaints)
    pending_tasks = Complaint.objects.filter(status='pending')[:10]

    context = {
        'total_complaints': total_complaints,
        'pending_complaints': pending_complaints,
        'assigned_complaints': assigned_complaints,
        'in_progress_complaints': in_progress_complaints,
        'completed_complaints': completed_complaints,
        'total_students': total_students,
        'total_professionals': total_professionals,
        'recent_complaints': recent_complaints,
        'professionals': professional_data,
        'pending_tasks': pending_tasks,
    }
    return render(request, 'dashboards/admin_dashboard.html', context)


@login_required
@user_passes_test(is_student)
def student_dashboard(request):
    """Student dashboard view"""
    # Get student's complaints
    student_complaints = Complaint.objects.filter(student=request.user)

    context = {
        'pending_complaints': student_complaints.filter(status='pending').count(),
        'assigned_complaints': student_complaints.filter(status='assigned').count(),
        'in_progress_complaints': student_complaints.filter(status='in_progress').count(),
        'completed_complaints': student_complaints.filter(status='completed').count(),
        'my_complaints': student_complaints.order_by('-created_at')[:10],
    }
    return render(request, 'dashboards/student_dashboard.html', context)


@login_required
@user_passes_test(is_professional)
def professional_dashboard(request):
    """Professional dashboard view"""
    # Get complaints assigned to this professional
    assigned_complaints = Complaint.objects.filter(assigned_to=request.user)

    context = {
        'assigned_complaints': assigned_complaints.filter(status='assigned').count(),
        'in_progress_complaints': assigned_complaints.filter(status='in_progress').count(),
        'completed_complaints': assigned_complaints.filter(status='completed').count(),
        'my_tasks': assigned_complaints.order_by('-created_at')[:10],
    }
    return render(request, 'dashboards/specialist_dashboard.html', context)


# ==================== PROFILE VIEW ====================
@login_required
def profile(request):
    # Ensure profile exists
    profile, created = UserProfile.objects.get_or_create(user=request.user)
    return render(request, 'hostelapp/profile.html', {'user': request.user, 'profile': profile})


# ==================== COMPLAINT VIEWS ====================
@login_required
def complaint_list(request):
    user = request.user
    # Ensure profile exists
    profile, created = UserProfile.objects.get_or_create(user=user)
    user_type = profile.user_type

    if user_type == 'admin':
        complaints = Complaint.objects.all()
    elif user_type == 'professional':
        complaints = Complaint.objects.filter(
            Q(assigned_to=user) | Q(status='pending')
        )
    else:  # student
        complaints = Complaint.objects.filter(student=user)

    # Filter by status if provided
    status = request.GET.get('status')
    if status:
        complaints = complaints.filter(status=status)

    # Pagination
    paginator = Paginator(complaints.order_by('-created_at'), 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    return render(request, 'hostelapp/complaint_list.html', {
        'complaints': page_obj,
        'status_filter': status,
        'user_type': user_type
    })


@login_required
def complaint_detail(request, complaint_id):
    complaint = get_object_or_404(Complaint, id=complaint_id)
    user = request.user
    # Ensure profile exists
    profile, created = UserProfile.objects.get_or_create(user=user)
    user_type = profile.user_type

    # Check permissions
    if user_type == 'student' and complaint.student != user:
        messages.error(request, 'You cannot view this complaint.')
        return redirect('hostelapp:dashboard')

    if user_type == 'professional' and complaint.assigned_to != user and complaint.status == 'pending':
        # Professionals can view pending complaints even if not assigned
        pass
    elif user_type == 'professional' and complaint.assigned_to != user:
        messages.error(request, 'This complaint is not assigned to you.')
        return redirect('hostelapp:dashboard')

    updates = complaint.updates.all()

    return render(request, 'hostelapp/complaint_detail.html', {
        'complaint': complaint,
        'updates': updates,
        'user_type': user_type
    })


@login_required
@user_passes_test(is_student)
def create_complaint(request):
    """Create a new complaint"""
    if request.method == 'POST':
        form = ComplaintForm(request.POST)
        if form.is_valid():
            complaint = form.save(commit=False)
            complaint.student = request.user
            complaint.status = 'pending'
            complaint.save()

            # Create initial update
            ComplaintUpdate.objects.create(
                complaint=complaint,
                user=request.user,
                message='Complaint submitted.'
            )

            messages.success(request, 'Complaint created successfully!')
            return redirect('hostelapp:complaint_detail', complaint_id=complaint.id)
    else:
        form = ComplaintForm()

    return render(request, 'hostelapp/create_complaint.html', {'form': form})


@login_required
def update_complaint_status(request, complaint_id):
    """Update complaint status"""
    complaint = get_object_or_404(Complaint, id=complaint_id)
    user = request.user
    profile, created = UserProfile.objects.get_or_create(user=user)
    user_type = profile.user_type

    # Check permissions
    if user_type == 'professional' and complaint.assigned_to != user:
        messages.error(request, 'You cannot update this complaint.')
        return redirect('hostelapp:dashboard')

    if user_type == 'student' and complaint.student != user:
        messages.error(request, 'You cannot update this complaint.')
        return redirect('hostelapp:dashboard')

    if request.method == 'POST':
        new_status = request.POST.get('status')
        message = request.POST.get('message', '')

        if new_status in dict(Complaint.STATUS_CHOICES):
            old_status = complaint.status
            complaint.status = new_status

            if new_status == 'completed':
                complaint.completed_at = timezone.now()

            complaint.save()

            # Create update record
            ComplaintUpdate.objects.create(
                complaint=complaint,
                user=user,
                message=message or f'Status changed from {old_status} to {new_status}',
                status_change=new_status
            )

            messages.success(request, f'Complaint status updated to {new_status}')

    return redirect('hostelapp:complaint_detail', complaint_id=complaint.id)


# ==================== ADMIN ASSIGNMENT VIEWS ====================
@login_required
@user_passes_test(is_admin)
def assign_complaint(request, complaint_id):
    """View to assign complaint to professional"""
    complaint = get_object_or_404(Complaint, id=complaint_id)

    if request.method == 'POST':
        professional_id = request.POST.get('professional')
        professional = get_object_or_404(User, id=professional_id)

        complaint.assigned_to = professional
        complaint.status = 'assigned'
        complaint.save()

        # Create an update record
        ComplaintUpdate.objects.create(
            complaint=complaint,
            user=request.user,
            message=f'Complaint assigned to {professional.get_full_name() or professional.username}',
            status_change='assigned'
        )

        messages.success(request,
                         f'Complaint #{complaint.id} assigned to {professional.get_full_name() or professional.username}')
        return redirect('hostelapp:complaint_list')

    professionals = User.objects.filter(profile__user_type='professional', is_active=True)
    return render(request, 'hostelapp/assign_complaint.html', {
        'complaint': complaint,
        'professionals': professionals
    })


@login_required
@user_passes_test(is_admin)
def professional_list(request):
    """View to list all professionals"""
    professionals = User.objects.filter(profile__user_type='professional', is_active=True)

    professional_data = []
    for prof in professionals:
        # Get active complaints
        active_complaints = Complaint.objects.filter(
            assigned_to=prof,
            status__in=['assigned', 'in_progress']
        ).count()

        # Get completed complaints
        completed_complaints = Complaint.objects.filter(
            assigned_to=prof,
            status='completed'
        ).count()

        # Get total assigned
        total_assigned = Complaint.objects.filter(assigned_to=prof).count()

        professional_data.append({
            'user': prof,
            'profile': prof.profile,
            'active_complaints': active_complaints,
            'completed_complaints': completed_complaints,
            'total_assigned': total_assigned
        })

    return render(request, 'hostelapp/professional_list.html', {'professionals': professional_data})


# ==================== TASK VIEWS ====================
@login_required
@user_passes_test(is_professional)
def my_tasks(request):
    """View for professionals to see their assigned tasks"""
    tasks = Complaint.objects.filter(assigned_to=request.user).order_by('-created_at')

    context = {
        'tasks': tasks,
        'pending_count': tasks.filter(status='assigned').count(),
        'in_progress_count': tasks.filter(status='in_progress').count(),
        'completed_count': tasks.filter(status='completed').count(),
    }
    return render(request, 'hostelapp/my_tasks.html', context)


# ==================== USER MANAGEMENT VIEWS ====================
@login_required
@user_passes_test(is_admin)
def create_user(request):
    if request.method == 'POST':
        form = UserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            user_type = form.cleaned_data.get('user_type', 'student')
            UserProfile.objects.create(user=user, user_type=user_type)
            messages.success(request, f'User {user.username} created successfully!')
            return redirect('hostelapp:user_list')
    else:
        form = UserCreationForm()

    return render(request, 'hostelapp/create_user.html', {'form': form})


@login_required
@user_passes_test(is_admin)
def user_list(request):
    students = User.objects.filter(profile__user_type='student')
    professionals = User.objects.filter(profile__user_type='professional')
    admins = User.objects.filter(Q(is_staff=True) | Q(is_superuser=True))

    return render(request, 'hostelapp/user_list.html', {
        'students': students,
        'professionals': professionals,
        'admins': admins
    })


@login_required
@user_passes_test(is_admin)
def toggle_user_status(request, user_id):
    """Activate or deactivate a user"""
    user = get_object_or_404(User, id=user_id)

    # Don't allow deactivating yourself
    if user == request.user:
        messages.error(request, 'You cannot deactivate your own account!')
        return redirect('hostelapp:user_list')

    user.is_active = not user.is_active
    user.save()

    status = "activated" if user.is_active else "deactivated"
    messages.success(request, f'User {user.username} has been {status}.')

    return redirect('hostelapp:user_list')


# ==================== ACCOUNT CREATION VIEWS ====================
@login_required
@user_passes_test(is_admin)
def create_student_account(request):
    """View for admin to create student accounts"""
    if request.method == 'POST':
        username = request.POST.get('username')
        email = request.POST.get('email')
        password = request.POST.get('password')
        first_name = request.POST.get('first_name')
        last_name = request.POST.get('last_name')
        room_number = request.POST.get('room_number')
        phone_number = request.POST.get('phone_number')

        # Check if username already exists
        if User.objects.filter(username=username).exists():
            messages.error(request, 'Username already exists!')
            return render(request, 'hostelapp/create_student.html')

        # Check if email already exists
        if User.objects.filter(email=email).exists():
            messages.error(request, 'Email already exists!')
            return render(request, 'hostelapp/create_student.html')

        try:
            # Create user
            user = User.objects.create_user(
                username=username,
                email=email,
                password=password,
                first_name=first_name,
                last_name=last_name
            )

            # Create user profile for student
            UserProfile.objects.create(
                user=user,
                user_type='student',
                phone_number=phone_number,
                room_number=room_number
            )

            messages.success(request, f'Student account created successfully for {username}')
            return redirect('hostelapp:admin_dashboard')

        except Exception as e:
            messages.error(request, f'Error creating account: {str(e)}')
            return render(request, 'hostelapp/create_student.html')

    return render(request, 'hostelapp/create_student.html')


@login_required
@user_passes_test(is_admin)
def create_professional_account(request):
    """View for admin to create professional accounts"""
    if request.method == 'POST':
        username = request.POST.get('username')
        email = request.POST.get('email')
        password = request.POST.get('password')
        first_name = request.POST.get('first_name')
        last_name = request.POST.get('last_name')
        specialization = request.POST.get('specialization')
        phone_number = request.POST.get('phone_number')

        # Check if username already exists
        if User.objects.filter(username=username).exists():
            messages.error(request, 'Username already exists!')
            return render(request, 'hostelapp/create_professional.html')

        # Check if email already exists
        if User.objects.filter(email=email).exists():
            messages.error(request, 'Email already exists!')
            return render(request, 'hostelapp/create_professional.html')

        try:
            # Create user
            user = User.objects.create_user(
                username=username,
                email=email,
                password=password,
                first_name=first_name,
                last_name=last_name
            )

            # Create user profile for professional
            UserProfile.objects.create(
                user=user,
                user_type='professional',
                phone_number=phone_number,
                specialization=specialization
            )

            messages.success(request, f'Professional account created successfully for {username}')
            return redirect('hostelapp:admin_dashboard')

        except Exception as e:
            messages.error(request, f'Error creating account: {str(e)}')
            return render(request, 'hostelapp/create_professional.html')

    return render(request, 'hostelapp/create_professional.html')


# ==================== BULK UPLOAD VIEWS ====================
@login_required
@user_passes_test(is_admin)
def bulk_upload_students(request):
    """View to bulk upload students via CSV"""
    if request.method == 'POST' and request.FILES.get('csv_file'):
        csv_file = request.FILES['csv_file']

        if not csv_file.name.endswith('.csv'):
            messages.error(request, 'File is not CSV type')
            return redirect('hostelapp:admin_dashboard')

        try:
            decoded_file = csv_file.read().decode('utf-8').splitlines()
            reader = csv.DictReader(decoded_file)

            success_count = 0
            error_count = 0
            errors = []

            for row_num, row in enumerate(reader, start=2):
                try:
                    username = row.get('username', '').strip()
                    email = row.get('email', '').strip()
                    first_name = row.get('first_name', '').strip()
                    last_name = row.get('last_name', '').strip()
                    room_number = row.get('room_number', '').strip()
                    phone_number = row.get('phone_number', '').strip()

                    # Validate required fields
                    if not username or not email:
                        errors.append(f"Row {row_num}: Username and email are required")
                        error_count += 1
                        continue

                    # Check if user exists
                    if User.objects.filter(username=username).exists():
                        errors.append(f"Row {row_num}: Username '{username}' already exists")
                        error_count += 1
                        continue

                    if User.objects.filter(email=email).exists():
                        errors.append(f"Row {row_num}: Email '{email}' already exists")
                        error_count += 1
                        continue

                    # Create user with default password
                    user = User.objects.create_user(
                        username=username,
                        email=email,
                        password='Student@123',  # Default password
                        first_name=first_name,
                        last_name=last_name
                    )

                    # Create student profile
                    UserProfile.objects.create(
                        user=user,
                        user_type='student',
                        room_number=room_number,
                        phone_number=phone_number
                    )
                    success_count += 1

                except Exception as e:
                    errors.append(f"Row {row_num}: {str(e)}")
                    error_count += 1

            if success_count > 0:
                messages.success(request, f'Successfully created {success_count} student accounts.')
            if error_count > 0:
                messages.warning(request, f'Failed to create {error_count} accounts.')
                if errors:
                    request.session['bulk_upload_errors'] = errors

        except Exception as e:
            messages.error(request, f'Error processing file: {str(e)}')

        return redirect('hostelapp:admin_dashboard')

    return redirect('hostelapp:admin_dashboard')


@login_required
@user_passes_test(is_admin)
def download_sample_csv(request):
    """Download sample CSV template for bulk upload"""
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="sample_students.csv"'

    writer = csv.writer(response)
    writer.writerow(['username', 'email', 'first_name', 'last_name', 'room_number', 'phone_number'])
    writer.writerow(['john.doe', 'john@example.com', 'John', 'Doe', 'A101', '1234567890'])
    writer.writerow(['jane.smith', 'jane@example.com', 'Jane', 'Smith', 'B202', '0987654321'])

    return response


# ==================== REPORT VIEWS ====================
@login_required
@user_passes_test(is_admin)
def generate_report(request):
    # Get filter parameters
    date_from = request.GET.get('from')
    date_to = request.GET.get('to')
    status = request.GET.get('status')

    complaints = Complaint.objects.all()

    if date_from:
        complaints = complaints.filter(created_at__gte=date_from)
    if date_to:
        complaints = complaints.filter(created_at__lte=date_to)
    if status:
        complaints = complaints.filter(status=status)

    # Statistics
    total = complaints.count()
    by_status = complaints.values('status').annotate(count=Count('id'))
    by_priority = complaints.values('priority').annotate(count=Count('id'))
    avg_completion_time = None

    completed = complaints.filter(status='completed', completed_at__isnull=False)
    if completed.exists():
        total_time = sum([(c.completed_at - c.created_at).total_seconds() for c in completed])
        avg_completion_time = total_time / completed.count() / 3600  # in hours

    return render(request, 'hostelapp/report.html', {
        'complaints': complaints,
        'total': total,
        'by_status': by_status,
        'by_priority': by_priority,
        'avg_completion_time': avg_completion_time,
        'date_from': date_from,
        'date_to': date_to,
        'selected_status': status
    })


@login_required
@user_passes_test(is_admin)
def download_pdf_report(request):
    # Create a file-like buffer to receive PDF data
    buffer = io.BytesIO()

    # Create the PDF object
    doc = SimpleDocTemplate(buffer, pagesize=A4, rightMargin=72, leftMargin=72, topMargin=72, bottomMargin=72)

    # Container for the 'Flowable' objects
    elements = []

    # Get styles
    styles = getSampleStyleSheet()
    title_style = styles['Heading1']
    heading_style = styles['Heading2']
    normal_style = styles['Normal']

    # Title
    elements.append(Paragraph('Hostel Assist - Complaint Report', title_style))
    elements.append(Paragraph(f'Generated on: {datetime.now().strftime("%Y-%m-%d %H:%M")}', normal_style))
    elements.append(Spacer(1, 0.2 * inch))

    # Get filter parameters
    date_from = request.GET.get('from')
    date_to = request.GET.get('to')
    status = request.GET.get('status')

    complaints = Complaint.objects.all()

    if date_from:
        complaints = complaints.filter(created_at__gte=date_from)
    if date_to:
        complaints = complaints.filter(created_at__lte=date_to)
    if status:
        complaints = complaints.filter(status=status)

    # Statistics
    total = complaints.count()
    elements.append(Paragraph(f'Total Complaints: {total}', heading_style))
    elements.append(Spacer(1, 0.2 * inch))

    # Status breakdown
    elements.append(Paragraph('Status Breakdown:', heading_style))
    status_counts = complaints.values('status').annotate(count=Count('id'))
    status_data = [['Status', 'Count']]
    for item in status_counts:
        status_data.append([item['status'], str(item['count'])])

    status_table = Table(status_data)
    status_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.green),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 14),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
        ('GRID', (0, 0), (-1, -1), 1, colors.black)
    ]))
    elements.append(status_table)
    elements.append(Spacer(1, 0.3 * inch))

    # Complaints table
    elements.append(Paragraph('Complaint Details:', heading_style))

    # Prepare data for table
    table_data = [['ID', 'Title', 'Student', 'Status', 'Priority', 'Created']]
    for complaint in complaints[:50]:  # Limit to 50 for PDF
        table_data.append([
            str(complaint.id),
            complaint.title[:30] + '...' if len(complaint.title) > 30 else complaint.title,
            complaint.student.username,
            complaint.status,
            complaint.priority,
            complaint.created_at.strftime('%Y-%m-%d')
        ])

    complaint_table = Table(table_data, colWidths=[0.5 * inch, 2 * inch, 1 * inch, 1 * inch, 1 * inch, 1.2 * inch])
    complaint_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.green),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 12),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
        ('GRID', (0, 0), (-1, -1), 1, colors.black)
    ]))
    elements.append(complaint_table)

    # Build PDF
    doc.build(elements)

    # Get the value of the buffer
    pdf = buffer.getvalue()
    buffer.close()

    # Create the HTTP response
    response = HttpResponse(content_type='application/pdf')
    response[
        'Content-Disposition'] = f'attachment; filename="complaint_report_{datetime.now().strftime("%Y%m%d_%H%M")}.pdf"'
    response.write(pdf)

    return response


# ==================== PROFESSIONAL TASK MANAGEMENT ====================
@login_required
@user_passes_test(is_professional)
def update_task_status(request, task_id):
    """View for professionals to update their task status"""
    task = get_object_or_404(Complaint, id=task_id, assigned_to=request.user)

    if request.method == 'POST':
        new_status = request.POST.get('status')
        message = request.POST.get('message', '')

        if new_status in dict(Complaint.STATUS_CHOICES):
            old_status = task.status
            task.status = new_status

            if new_status == 'completed':
                task.completed_at = timezone.now()

            task.save()

            # Create update record
            ComplaintUpdate.objects.create(
                complaint=task,
                user=request.user,
                message=message or f'Task status changed from {old_status} to {new_status}',
                status_change=new_status
            )

            messages.success(request, f'Task status updated to {new_status}')
            return redirect('hostelapp:my_tasks')

    return render(request, 'hostelapp/update_task_status.html', {'task': task})


# ==================== ADMIN PROFESSIONAL MANAGEMENT ====================
@login_required
@user_passes_test(is_admin)
def professional_detail(request, professional_id):
    """View for admin to see professional details and their assigned tasks"""
    professional_user = get_object_or_404(User, id=professional_id, profile__user_type='professional')

    # Get all complaints assigned to this professional
    assigned_complaints = Complaint.objects.filter(assigned_to=professional_user).order_by('-created_at')

    # Statistics
    total_assigned = assigned_complaints.count()
    active_tasks = assigned_complaints.filter(status__in=['assigned', 'in_progress']).count()
    completed_tasks = assigned_complaints.filter(status='completed').count()

    context = {
        'professional': professional_user,
        'profile': professional_user.profile,
        'assigned_complaints': assigned_complaints,
        'total_assigned': total_assigned,
        'active_tasks': active_tasks,
        'completed_tasks': completed_tasks,
    }
    return render(request, 'dashboards/specialist_dashboard.html', context)


# ==================== ADMIN TASK MANAGEMENT ====================
@login_required
@user_passes_test(is_admin)
def task_list(request):
    """View for admin to see all tasks/complaints"""
    # Get filter parameters
    status = request.GET.get('status')
    priority = request.GET.get('priority')
    assigned = request.GET.get('assigned')

    tasks = Complaint.objects.all().select_related('student', 'assigned_to')

    if status:
        tasks = tasks.filter(status=status)
    if priority:
        tasks = tasks.filter(priority=priority)
    if assigned == 'yes':
        tasks = tasks.filter(assigned_to__isnull=False)
    elif assigned == 'no':
        tasks = tasks.filter(assigned_to__isnull=True)

    # Statistics
    total_tasks = tasks.count()
    pending_count = tasks.filter(status='pending').count()
    in_progress_count = tasks.filter(status='in_progress').count()
    completed_count = tasks.filter(status='completed').count()

    # Pagination
    paginator = Paginator(tasks.order_by('-created_at'), 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    context = {
        'tasks': page_obj,
        'total_tasks': total_tasks,
        'pending_count': pending_count,
        'in_progress_count': in_progress_count,
        'completed_count': completed_count,
        'current_status': status,
        'current_priority': priority,
        'current_assigned': assigned,
    }
    return render(request, 'hostelapp/task_list.html', context)


@login_required
@user_passes_test(is_admin)
def assign_task(request):
    """View for admin to assign tasks to professionals"""
    if request.method == 'POST':
        complaint_id = request.POST.get('complaint')
        professional_id = request.POST.get('professional')

        if complaint_id and professional_id:
            complaint = get_object_or_404(Complaint, id=complaint_id)
            professional = get_object_or_404(User, id=professional_id, profile__user_type='professional')

            complaint.assigned_to = professional
            complaint.status = 'assigned'
            complaint.save()

            # Create update record
            ComplaintUpdate.objects.create(
                complaint=complaint,
                user=request.user,
                message=f'Task assigned to {professional.get_full_name() or professional.username}',
                status_change='assigned'
            )

            messages.success(request, f'Task #{complaint.id} assigned to {professional.username}')
            return redirect('hostelapp:task_list')

    # Get unassigned complaints
    unassigned_complaints = Complaint.objects.filter(assigned_to__isnull=True, status='pending')
    professionals = User.objects.filter(profile__user_type='professional', is_active=True)

    context = {
        'unassigned_complaints': unassigned_complaints,
        'professionals': professionals,
    }
    return render(request, 'hostelapp/assign_task.html', context)


@login_required
@user_passes_test(is_admin)
def update_task(request, task_id):
    """View for admin to update task details"""
    task = get_object_or_404(Complaint, id=task_id)

    if request.method == 'POST':
        # Update basic fields
        task.title = request.POST.get('title', task.title)
        task.description = request.POST.get('description', task.description)
        task.priority = request.POST.get('priority', task.priority)

        # Handle status change
        new_status = request.POST.get('status')
        if new_status and new_status != task.status:
            old_status = task.status
            task.status = new_status

            if new_status == 'completed' and not task.completed_at:
                task.completed_at = timezone.now()

            # Create update record for status change
            ComplaintUpdate.objects.create(
                complaint=task,
                user=request.user,
                message=f'Status changed from {old_status} to {new_status} by admin',
                status_change=new_status
            )

        # Handle reassignment
        new_professional_id = request.POST.get('assigned_to')
        if new_professional_id:
            try:
                new_professional = User.objects.get(id=new_professional_id, profile__user_type='professional')
                if task.assigned_to != new_professional:
                    old_professional = task.assigned_to
                    task.assigned_to = new_professional

                    # Create update record for reassignment
                    ComplaintUpdate.objects.create(
                        complaint=task,
                        user=request.user,
                        message=f'Reassigned from {old_professional.username if old_professional else "Unassigned"} to {new_professional.username}'
                    )
            except User.DoesNotExist:
                pass

        task.save()
        messages.success(request, f'Task #{task.id} updated successfully')
        return redirect('hostelapp:task_list')

    # Get all professionals for reassignment dropdown
    professionals = User.objects.filter(profile__user_type='professional', is_active=True)

    context = {
        'task': task,
        'professionals': professionals,
    }
    return render(request, 'hostelapp/update_task.html', context)


# ==================== STUDENT COMPLAINT VIEWS ====================
@login_required
@user_passes_test(is_student)
def my_complaints(request):
    """View for students to see their own complaints"""
    complaints = Complaint.objects.filter(student=request.user).order_by('-created_at')

    # Statistics
    total = complaints.count()
    pending = complaints.filter(status='pending').count()
    assigned = complaints.filter(status='assigned').count()
    in_progress = complaints.filter(status='in_progress').count()
    completed = complaints.filter(status='completed').count()

    # Pagination
    paginator = Paginator(complaints, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    context = {
        'complaints': page_obj,
        'total': total,
        'pending': pending,
        'assigned': assigned,
        'in_progress': in_progress,
        'completed': completed,
    }
    return render(request, 'hostelapp/my_complaints.html', context)


# ==================== PROFESSIONAL TASK MANAGEMENT ====================
@login_required
@user_passes_test(is_professional)
def update_task_status(request, task_id):
    """View for professionals to update their task status"""
    task = get_object_or_404(Complaint, id=task_id, assigned_to=request.user)

    if request.method == 'POST':
        new_status = request.POST.get('status')
        message = request.POST.get('message', '')

        if new_status in dict(Complaint.STATUS_CHOICES):
            old_status = task.status
            task.status = new_status

            if new_status == 'completed':
                task.completed_at = timezone.now()

            task.save()

            # Create update record
            ComplaintUpdate.objects.create(
                complaint=task,
                user=request.user,
                message=message or f'Task status changed from {old_status} to {new_status}',
                status_change=new_status
            )

            messages.success(request, f'Task status updated to {new_status}')
            return redirect('hostelapp:my_tasks')

    return render(request, 'hostelapp/update_task_status.html', {'task': task})


# ==================== ADMIN PROFESSIONAL MANAGEMENT ====================
@login_required
@user_passes_test(is_admin)
def professional_detail(request, professional_id):
    """View for admin to see professional details and their assigned tasks"""
    professional_user = get_object_or_404(User, id=professional_id, profile__user_type='professional')

    # Get all complaints assigned to this professional
    assigned_complaints = Complaint.objects.filter(assigned_to=professional_user).order_by('-created_at')

    # Statistics
    total_assigned = assigned_complaints.count()
    active_tasks = assigned_complaints.filter(status__in=['assigned', 'in_progress']).count()
    completed_tasks = assigned_complaints.filter(status='completed').count()

    context = {
        'professional': professional_user,
        'profile': professional_user.profile,
        'assigned_complaints': assigned_complaints,
        'total_assigned': total_assigned,
        'active_tasks': active_tasks,
        'completed_tasks': completed_tasks,
    }
    return render(request, 'hostelapp/professional_detail.html', context)


# ==================== ADMIN TASK MANAGEMENT ====================
@login_required
@user_passes_test(is_admin)
def task_list(request):
    """View for admin to see all tasks/complaints"""
    # Get filter parameters
    status = request.GET.get('status')
    priority = request.GET.get('priority')
    assigned = request.GET.get('assigned')

    tasks = Complaint.objects.all().select_related('student', 'assigned_to')

    if status:
        tasks = tasks.filter(status=status)
    if priority:
        tasks = tasks.filter(priority=priority)
    if assigned == 'yes':
        tasks = tasks.filter(assigned_to__isnull=False)
    elif assigned == 'no':
        tasks = tasks.filter(assigned_to__isnull=True)

    # Statistics
    total_tasks = tasks.count()
    pending_count = tasks.filter(status='pending').count()
    in_progress_count = tasks.filter(status='in_progress').count()
    completed_count = tasks.filter(status='completed').count()

    # Pagination
    paginator = Paginator(tasks.order_by('-created_at'), 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    context = {
        'tasks': page_obj,
        'total_tasks': total_tasks,
        'pending_count': pending_count,
        'in_progress_count': in_progress_count,
        'completed_count': completed_count,
        'current_status': status,
        'current_priority': priority,
        'current_assigned': assigned,
    }
    return render(request, 'hostelapp/task_list.html', context)


@login_required
@user_passes_test(is_admin)
def assign_task(request):
    """View for admin to assign tasks to professionals"""
    if request.method == 'POST':
        complaint_id = request.POST.get('complaint')
        professional_id = request.POST.get('professional')

        if complaint_id and professional_id:
            complaint = get_object_or_404(Complaint, id=complaint_id)
            professional = get_object_or_404(User, id=professional_id, profile__user_type='professional')

            complaint.assigned_to = professional
            complaint.status = 'assigned'
            complaint.save()

            # Create update record
            ComplaintUpdate.objects.create(
                complaint=complaint,
                user=request.user,
                message=f'Task assigned to {professional.get_full_name() or professional.username}',
                status_change='assigned'
            )

            messages.success(request, f'Task #{complaint.id} assigned to {professional.username}')
            return redirect('hostelapp:task_list')

    # Get unassigned complaints
    unassigned_complaints = Complaint.objects.filter(assigned_to__isnull=True, status='pending')
    professionals = User.objects.filter(profile__user_type='professional', is_active=True)

    context = {
        'unassigned_complaints': unassigned_complaints,
        'professionals': professionals,
    }
    return render(request, 'hostelapp/assign_task.html', context)


@login_required
@user_passes_test(is_admin)
def update_task(request, task_id):
    """View for admin to update task details"""
    task = get_object_or_404(Complaint, id=task_id)

    if request.method == 'POST':
        # Update basic fields
        task.title = request.POST.get('title', task.title)
        task.description = request.POST.get('description', task.description)
        task.priority = request.POST.get('priority', task.priority)

        # Handle status change
        new_status = request.POST.get('status')
        if new_status and new_status != task.status:
            old_status = task.status
            task.status = new_status

            if new_status == 'completed' and not task.completed_at:
                task.completed_at = timezone.now()

            # Create update record for status change
            ComplaintUpdate.objects.create(
                complaint=task,
                user=request.user,
                message=f'Status changed from {old_status} to {new_status} by admin',
                status_change=new_status
            )

        # Handle reassignment
        new_professional_id = request.POST.get('assigned_to')
        if new_professional_id:
            try:
                new_professional = User.objects.get(id=new_professional_id, profile__user_type='professional')
                if task.assigned_to != new_professional:
                    old_professional = task.assigned_to
                    task.assigned_to = new_professional

                    # Create update record for reassignment
                    ComplaintUpdate.objects.create(
                        complaint=task,
                        user=request.user,
                        message=f'Reassigned from {old_professional.username if old_professional else "Unassigned"} to {new_professional.username}'
                    )
            except User.DoesNotExist:
                pass

        task.save()
        messages.success(request, f'Task #{task.id} updated successfully')
        return redirect('hostelapp:task_list')

    # Get all professionals for reassignment dropdown
    professionals = User.objects.filter(profile__user_type='professional', is_active=True)

    context = {
        'task': task,
        'professionals': professionals,
    }
    return render(request, 'hostelapp/update_task.html', context)



def create_student_account(request):
    if request.method == 'POST':
        form = StudentRegistrationForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Student account created successfully!')
            return redirect('admin_dashboard')
    else:
        form = StudentRegistrationForm()
    return render(request, 'hostelapp/create_student.html', {'form': form})

def create_professional_account(request):
    if request.method == 'POST':
        form = ProfessionalRegistrationForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Professional account created successfully!')
            return redirect('admin_dashboard')
    else:
        form = ProfessionalRegistrationForm()
    return render(request, 'hostelapp/create_professional.html', {'form': form})  # Make sure template name matches


@login_required
def submit_complaint(request):
    # Check if user is a student
    if request.user.profile.user_type != 'student':
        messages.error(request, 'Only students can submit complaints.')
        return redirect('dashboard')

    if request.method == 'POST':
        form = ComplaintForm(request.POST, user=request.user)
        if form.is_valid():
            complaint = form.save(commit=False)
            complaint.student = request.user
            complaint.save()
            messages.success(request, 'Complaint submitted successfully!')
            return redirect('my_complaints')
    else:
        form = ComplaintForm(user=request.user)

    return render(request, 'hostelapp/submit_complaint.html', {'form': form})