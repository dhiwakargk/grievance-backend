from django.urls import path
from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    TokenRefreshView,
)
from . import views

urlpatterns = [
    # Auth
    path('register/', views.register_user, name='register'),
    path('login/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('user-info/', views.user_info, name='user_info'),
    
    # Departments
    path('departments/', views.department_list, name='department_list'),
    path('departments/<int:pk>/', views.department_detail, name='department_detail'),
    
    # Grievances
    path('grievances/', views.grievance_list_create, name='grievance_list_create'),
    path('grievances/<int:pk>/', views.grievance_detail, name='grievance_detail'),
    path('grievances/<int:pk>/status/', views.update_grievance_status, name='update_grievance_status'),
    
    # Officials Management
    path('manage-officials/', views.manage_officials, name='manage_officials'),

    # Stats
    path('stats/', views.dashboard_stats, name='dashboard_stats'),
]
