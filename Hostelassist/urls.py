from django.contrib import admin
from django.urls import path, include
from django.contrib.auth import views as auth_views

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('hostelapp.urls')),  # Include app URLs

    path('accounts/', include('django.contrib.auth.urls')),
]