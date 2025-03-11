from django.urls import path
from maintenance import views

urlpatterns = [
    # Authentication views
    path('', views.home, name='home'),
    path('login/', views.user_login, name='login'),
    path('logout/', views.user_logout, name='logout'),
    
    # User management (admin-only)
    path('users/', views.user_list, name='user_list'),
    path('users/add/', views.add_user, name='add_user'),
    path('users/<int:user_id>/edit/', views.edit_user, name='edit_user'),
    path('users/<int:user_id>/deactivate/', views.deactivate_user, name='deactivate_user'),
    path('users/<int:user_id>/reset-password/', views.reset_user_password, name='reset_password'),
    
    # Maintenance request views
    path('request/create/', views.create_maintenance_request, name='create_request'),
    path('request/<int:request_id>/', views.view_maintenance_request, name='view_maintenance_request'),
    path('request/<int:request_id>/update/', views.update_maintenance_request, name='update_maintenance_request'),
    path('request/<int:request_id>/assign/', views.assign_request, name='assign_request'),
    
    # Staff views
    path('staff/request-pool/', views.staff_request_pool, name='staff_request_pool'),
    path('staff/my-requests/', views.my_assigned_requests, name='my_assigned_requests'),
    
    # Inventory management
    path('inventory/', views.view_inventory, name='inventory'),
    path('inventory/add/', views.add_inventory_item, name='add_inventory'),
    path('inventory/<int:item_id>/edit/', views.edit_inventory_item, name='edit_inventory'),
    path('inventory/<int:item_id>/adjust/', views.adjust_inventory_quantity, name='adjust_inventory'),
    
    # Report generation
    path('report/generate/', views.generate_maintenance_report, name='generate_report'),
    path('report/<int:report_id>/', views.view_report, name='view_report'),
    
    # Category and building management (admin-only)
    path('categories/', views.category_list, name='category_list'),
    path('categories/add/', views.add_category, name='add_category'),
    path('buildings/', views.building_list, name='building_list'),
    path('buildings/add/', views.add_building, name='add_building'),

]