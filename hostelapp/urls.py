from django.urls import path, include
from django.contrib.auth import views as auth_views
from . import views
from django.shortcuts import redirect

app_name = 'hostelapp'

urlpatterns = [
    # Authentication - USE THE CUSTOM VIEW INSTEAD OF DEFAULT LoginView
    path('login/', views.role_based_login, name='login'),
    path('logout/', auth_views.LogoutView.as_view(next_page='login'), name='logout'),

    # Role-specific dashboards
    path('admin-dashboard/', views.admin_dashboard, name='admin_dashboard'),
    path('student-dashboard/', views.student_dashboard, name='student_dashboard'),
    path('professional-dashboard/', views.professional_dashboard, name='professional_dashboard'),
    # Using the same view but renamed URL

    # Original dashboard (can keep for backward compatibility or remove)
    path('dashboard/', views.dashboard, name='dashboard'),

    # Profile
    path('profile/', views.profile, name='profile'),

    # Complaints
    path('complaints/', views.complaint_list, name='complaint_list'),
    path('complaints/create/', views.create_complaint, name='create_complaint'),
    path('complaints/<int:complaint_id>/', views.complaint_detail, name='complaint_detail'),
    path('complaints/<int:complaint_id>/update/', views.update_complaint_status, name='update_complaint'),

    # Users
    path('users/', views.user_list, name='user_list'),

    # Reports
    path('reports/generate/', views.generate_report, name='generate_report'),

    # Student specific
    path('my-complaints/', views.my_complaints, name='my_complaints'),

    # Professional specific
    path('my-tasks/', views.my_tasks, name='my_tasks'),
    path('task/<int:task_id>/update/', views.update_task_status, name='update_task_status'),

    # Admin - Account Creation (UPDATED to use professional instead of specialist)
    path('admin/create-student/', views.create_student_account, name='create_student_account'),
    path('admin/create-professional/', views.create_professional_account, name='create_professional_account'),

    # Admin - Professional Management
    path('admin/professionals/', views.professional_list, name='professional_list'),
    path('admin/professional/<int:professional_id>/', views.professional_detail, name='professional_detail'),

    # Admin - Complaint Assignment
    path('admin/assign-complaint/<int:complaint_id>/', views.assign_complaint, name='assign_complaint'),

    # Admin - Task Management (UPDATED to be consistent)
    path('admin/tasks/', views.task_list, name='task_list'),
    path('admin/tasks/assign/', views.assign_task, name='assign_task'),
    path('admin/tasks/<int:task_id>/update/', views.update_task, name='update_task'),

    # Admin - Bulk Upload
    path('admin/bulk-upload-students/', views.bulk_upload_students, name='bulk_upload_students'),
    path('admin/download-sample-csv/', views.download_sample_csv, name='download_sample_csv'),

    # Root URL - redirect to login
    path('', lambda request: redirect('hostelapp:login'), name='root'),

    path('professionals/', views.professional_list, name='professional_list'),

   path('create-student/', views.create_student_account, name='create_student'),
   path('create-professional/', views.create_professional_account, name='create_professional'),

   path('submit-complaint/', views.submit_complaint, name='submit_complaint'),
   path('my-complaints/', views.my_complaints, name='my_complaints'),

    path('users/', views.user_list, name='user_list'),
    path('user/<int:user_id>/', views.user_detail, name='user_detail'),
    path('user/<int:user_id>/edit/', views.edit_user, name='edit_user'),
    path('user/<int:user_id>/delete/', views.delete_user, name='delete_user'),

    path('user/<int:user_id>/reset-password/', views.reset_password, name='reset_password'),
]