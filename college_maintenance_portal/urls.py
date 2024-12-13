from django.contrib import admin
from django.urls import path
from maintenance import views

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', views.home, name='home'),
    path('login/', views.user_login, name='login'),
    path('logout/', views.user_logout, name='logout'),
    path('register/', views.user_registration, name='register'),
    path('request/create/', views.create_maintenance_request, name='create_request'),
    path('request/<int:request_id>/', views.view_maintenance_request, name='view_maintenance_request'),
    path('request/<int:request_id>/update/', views.update_maintenance_request, name='update_request'),
    path('report/generate/', views.generate_maintenance_report, name='generate_report'),
    path('inventory/', views.view_inventory, name='inventory'),

     path('staff/request-pool/', views.staff_request_pool, name='staff_request_pool'),
    path('staff/my-requests/', views.my_assigned_requests, name='my_assigned_requests'),
    path('request/<int:request_id>/assign/', views.assign_request, name='assign_request'),
]