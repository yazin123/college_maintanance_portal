from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, authenticate, logout
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django.db.models import Count, Avg, Q, F, ExpressionWrapper, fields
from django.db.models.functions import Cast
from django.utils import timezone
from django.core.paginator import Paginator
from functools import wraps

from .models import (
    CustomUser, 
    MaintenanceRequest, 
    MaintenanceCategory, 
    Building, 
    MaintenanceLog, 
    InventoryItem, 
    MaintenanceReport
)
from .forms import (
    UserRegistrationForm,  # This will now be used by admins only
    MaintenanceRequestForm, 
    MaintenanceLogForm, 
    MaintenanceReportForm,
    InventoryItemForm,
    UserCreationForm,  # New form for admin to create users
    UserEditForm        # New form for admin to edit users
)

# Custom decorators
def staff_required(view_func):
    """
    Decorator for views that checks if the user is staff or admin
    """
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        if not request.user.is_authenticated:
            messages.error(request, 'You must be logged in to access this page')
            return redirect('login')
        if request.user.user_type not in ['staff', 'admin']:
            messages.error(request, 'You are not authorized to access this page')
            return redirect('home')
        return view_func(request, *args, **kwargs)
    return _wrapped_view

def admin_required(view_func):
    """
    Decorator for views that checks if the user is an admin
    """
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        if not request.user.is_authenticated:
            messages.error(request, 'You must be logged in to access this page')
            return redirect('login')
        if request.user.user_type != 'admin':
            messages.error(request, 'You are not authorized to access this page')
            return redirect('home')
        return view_func(request, *args, **kwargs)
    return _wrapped_view

def home(request):
    """
    Home page view with an overview of maintenance requests
    """
    if not request.user.is_authenticated:
        return render(request, 'home.html')
    
    # Different dashboard views based on user type
    if request.user.user_type == 'student':
        # Fetch student's maintenance requests with additional details
        all_requests = MaintenanceRequest.objects.filter(requester=request.user).select_related(
            'category', 'building'
        ).order_by('-created_at')
        
        # Pagination
        paginator = Paginator(all_requests, 10)  # Show 10 requests per page
        page_number = request.GET.get('page')
        requests = paginator.get_page(page_number)
        
        return render(request, 'student_dashboard.html', {
            'requests': requests
        })
    
    elif request.user.user_type == 'staff':
        # Fetch requests assigned to staff
        assigned_requests = MaintenanceRequest.objects.filter(
            assigned_to=request.user,
            status__in=['pending', 'in_progress']
        ).select_related('category', 'building', 'requester')
        
        # Fetch unassigned requests for the pool
        unassigned_requests = MaintenanceRequest.objects.filter(
            assigned_to__isnull=True
        ).select_related('category', 'building', 'requester')
        
        # Pagination for assigned requests
        paginator = Paginator(assigned_requests, 10)
        page_number = request.GET.get('page')
        paginated_assigned = paginator.get_page(page_number)
        
        return render(request, 'staff_dashboard.html', {
            'assigned_requests': paginated_assigned,
            'unassigned_count': unassigned_requests.count()
        })
    
    elif request.user.user_type == 'admin':
        # Comprehensive admin dashboard
        total_requests = MaintenanceRequest.objects.all()
        
        # Detailed request statistics
        request_stats = total_requests.values('status').annotate(
            count=Count('id')
        ).order_by('-count')
        
        # Most recent requests with related information
        recent_requests = total_requests.select_related(
            'requester', 'category', 'building', 'assigned_to'
        ).order_by('-created_at')[:10]
        
        # Additional metrics
        metrics = {
            'total_users': CustomUser.objects.count(),
            'student_count': CustomUser.objects.filter(user_type='student').count(),
            'staff_count': CustomUser.objects.filter(user_type='staff').count(),
            'total_buildings': Building.objects.count(),
            'total_categories': MaintenanceCategory.objects.count(),
            'pending_requests': total_requests.filter(status='pending').count(),
            'in_progress_requests': total_requests.filter(status='in_progress').count(),
            'completed_requests': total_requests.filter(status='completed').count(),
        }
        
        return render(request, 'admin_dashboard.html', {
            'total_requests': total_requests,
            'request_stats': request_stats,
            'recent_requests': recent_requests,
            'metrics': metrics
        })

def user_login(request):
    """
    User login view
    """
    if request.user.is_authenticated:
        return redirect('home')
        
    if request.method == 'POST':
        username = request.POST['username']
        password = request.POST['password']
        user = authenticate(request, username=username, password=password)
        
        if user is not None:
            login(request, user)
            next_url = request.GET.get('next', 'home')
            messages.success(request, 'Login successful!')
            return redirect(next_url)
        else:
            messages.error(request, 'Invalid login credentials')
    
    return render(request, 'login.html')

def user_logout(request):
    """
    User logout view
    """
    logout(request)
    messages.success(request, 'You have been logged out.')
    return redirect('home')

# Remove the public registration view
# Instead, add admin-only user management views

@login_required
@admin_required
def user_list(request):
    """
    Admin view to list all users
    """
    # Get user type filter if present
    user_type = request.GET.get('user_type', '')
    
    # Filter users based on type if selected
    if user_type and user_type in ['student', 'staff', 'admin']:
        users = CustomUser.objects.filter(user_type=user_type).order_by('username')
    else:
        users = CustomUser.objects.all().order_by('username')
    
    # Pagination
    paginator = Paginator(users, 20)  # Show 20 users per page
    page_number = request.GET.get('page')
    paginated_users = paginator.get_page(page_number)
    
    # Count by user type
    user_counts = {
        'students': CustomUser.objects.filter(user_type='student').count(),
        'staff': CustomUser.objects.filter(user_type='staff').count(),
        'admins': CustomUser.objects.filter(user_type='admin').count(),
        'total': CustomUser.objects.count()
    }
    
    return render(request, 'user_list.html', {
        'users': paginated_users,
        'user_counts': user_counts,
        'current_filter': user_type
    })

@login_required
@admin_required
def add_user(request):
    """
    Admin view to add a new user (student or staff)
    """
    if request.method == 'POST':
        form = UserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            messages.success(request, f"User '{user.username}' created successfully!")
            return redirect('user_list')
    else:
        form = UserCreationForm()
    
    return render(request, 'user_form.html', {
        'form': form,
        'title': 'Add New User',
        'button_text': 'Create User'
    })

@login_required
@admin_required
def edit_user(request, user_id):
    """
    Admin view to edit an existing user
    """
    user = get_object_or_404(CustomUser, id=user_id)
    
    if request.method == 'POST':
        form = UserEditForm(request.POST, instance=user)
        if form.is_valid():
            form.save()
            messages.success(request, f"User '{user.username}' updated successfully!")
            return redirect('user_list')
    else:
        form = UserEditForm(instance=user)
    
    return render(request, 'user_form.html', {
        'form': form,
        'user': user,
        'title': f'Edit User: {user.username}',
        'button_text': 'Save Changes'
    })

@login_required
@admin_required
def deactivate_user(request, user_id):
    """
    Admin view to deactivate a user
    """
    user = get_object_or_404(CustomUser, id=user_id)
    
    # Prevent deactivating own account
    if user == request.user:
        messages.error(request, "You cannot deactivate your own account!")
        return redirect('user_list')
    
    if request.method == 'POST':
        user.is_active = False
        user.save()
        messages.success(request, f"User '{user.username}' has been deactivated.")
        return redirect('user_list')
    
    return render(request, 'confirm_deactivate.html', {
        'user': user
    })

@login_required
@admin_required
def reset_user_password(request, user_id):
    """
    Admin view to reset a user's password
    """
    user = get_object_or_404(CustomUser, id=user_id)
    
    if request.method == 'POST':
        # Set a default password (e.g., their username + "123")
        default_password = f"{user.username}123"
        user.set_password(default_password)
        user.save()
        
        messages.success(request, f"Password for '{user.username}' has been reset to: {default_password}")
        return redirect('user_list')
    
    return render(request, 'confirm_reset_password.html', {
        'user': user
    })

@login_required
def create_maintenance_request(request):
    """
    View for creating a new maintenance request
    """
    # Only students and admins can create requests
    if request.user.user_type not in ['student', 'admin']:
        messages.error(request, 'Only students can submit maintenance requests')
        return redirect('home')
        
    if request.method == 'POST':
        form = MaintenanceRequestForm(request.POST)
        if form.is_valid():
            maintenance_request = form.save(commit=False)
            maintenance_request.requester = request.user
            maintenance_request.save()
            
            # Create initial log entry
            MaintenanceLog.objects.create(
                request=maintenance_request,
                staff_member=request.user,
                description=f"Maintenance request submitted by {request.user.username}"
            )
            
            messages.success(request, 'Maintenance request submitted successfully!')
            return redirect('view_maintenance_request', request_id=maintenance_request.id)
    else:
        form = MaintenanceRequestForm()
    
    # Get available categories and buildings for context
    categories = MaintenanceCategory.objects.all()
    buildings = Building.objects.all()
    
    return render(request, 'create_request.html', {
        'form': form,
        'categories': categories,
        'buildings': buildings
    })

@login_required
def view_maintenance_request(request, request_id):
    """
    View details of a specific maintenance request
    """
    maintenance_request = get_object_or_404(
        MaintenanceRequest.objects.select_related('requester', 'category', 'building', 'assigned_to'), 
        id=request_id
    )
    
    # Check user permissions
    if (request.user.user_type == 'student' and 
        maintenance_request.requester != request.user):
        messages.error(request, 'You are not authorized to view this request')
        return redirect('home')
    
    logs = MaintenanceLog.objects.filter(request=maintenance_request).select_related('staff_member').order_by('-timestamp')
    
    # Get staff users for admin assignment dropdown
    staff_users = []
    if request.user.user_type == 'admin':
        staff_users = CustomUser.objects.filter(user_type='staff', is_active=True).order_by('username')
    
    return render(request, 'request_detail.html', {
        'request': maintenance_request,
        'logs': logs,
        'staff_users': staff_users
    })


@login_required
@staff_required
def update_maintenance_request(request, request_id):
    """
    Update status of a maintenance request
    """
    maintenance_request = get_object_or_404(
        MaintenanceRequest, 
        id=request_id
    )
    
    # Check if staff is assigned to this request or is admin
    if (request.user.user_type == 'staff' and 
        maintenance_request.assigned_to != request.user and 
        maintenance_request.assigned_to is not None):
        messages.error(request, 'You are not authorized to update this request')
        return redirect('home')
    
    if request.method == 'POST':
        new_status = request.POST.get('status')
        log_description = request.POST.get('log_description', '')
        
        # Validate input
        if not log_description:
            messages.error(request, 'Log description is required')
            return render(request, 'update_request.html', {'request': maintenance_request})
        
        # Check for valid status transition
        if maintenance_request.status == 'completed' and new_status != 'completed':
            messages.warning(request, 'Request has already been completed')
        
        # Auto-assign to staff if unassigned and staff is updating
        if maintenance_request.assigned_to is None and request.user.user_type == 'staff':
            maintenance_request.assigned_to = request.user
            messages.info(request, 'Request has been automatically assigned to you')
        
        # Update request status
        maintenance_request.status = new_status
        maintenance_request.save()
        
        # Create log entry
        log = MaintenanceLog.objects.create(
            request=maintenance_request,
            staff_member=request.user,
            description=log_description
        )
        
        messages.success(request, 'Request updated successfully!')
        return redirect('view_maintenance_request', request_id=maintenance_request.id)
    
    return render(request, 'update_request.html', {
        'request': maintenance_request
    })

@login_required
@admin_required
def generate_maintenance_report(request):
    """
    Generate maintenance performance report
    """
    if request.method == 'POST':
        form = MaintenanceReportForm(request.POST)
        if form.is_valid():
            start_date = form.cleaned_data['start_date']
            end_date = form.cleaned_data['end_date']
            
            # Validate date range
            if end_date < start_date:
                messages.error(request, 'End date must be after start date')
                return render(request, 'generate_report.html', {'form': form})
            
            # Get requests in the date range
            requests = MaintenanceRequest.objects.filter(
                created_at__range=[start_date, end_date]
            )
            
            # Calculate average resolution time properly
            completed_requests = requests.filter(status='completed')
            avg_time = None
            
            if completed_requests.exists():
                avg_time = completed_requests.annotate(
                    resolution_time=ExpressionWrapper(
                        F('updated_at') - F('created_at'),
                        output_field=fields.DurationField()
                    )
                ).aggregate(avg=Avg('resolution_time'))['avg']
            
            # Convert to hours
            avg_hours = 0
            if avg_time:
                avg_hours = avg_time.total_seconds() / 3600
            
            # Create report object
            report = MaintenanceReport.objects.create(
                generated_by=request.user,
                start_date=start_date,
                end_date=end_date,
                total_requests=requests.count(),
                completed_requests=completed_requests.count(),
                average_resolution_time=avg_hours
            )
            
            messages.success(request, 'Report generated successfully!')
            return redirect('view_report', report_id=report.id)
    else:
        # Default to last 30 days
        end_date = timezone.now().date()
        start_date = end_date - timezone.timedelta(days=30)
        form = MaintenanceReportForm(initial={'start_date': start_date, 'end_date': end_date})
    
    # Get list of recent reports
    recent_reports = MaintenanceReport.objects.order_by('-generated_at')[:5]
    
    return render(request, 'generate_report.html', {
        'form': form,
        'recent_reports': recent_reports
    })

@login_required
@admin_required
def view_report(request, report_id):
    """
    View a generated maintenance report
    """
    report = get_object_or_404(MaintenanceReport, id=report_id)
    
    # Get requests within the report date range
    requests = MaintenanceRequest.objects.filter(
        created_at__range=[report.start_date, report.end_date]
    ).select_related('category', 'building', 'requester', 'assigned_to')
    
    # Get category breakdown
    category_stats = requests.values('category__name').annotate(
        count=Count('id')
    ).order_by('-count')
    
    # Get building breakdown
    building_stats = requests.values('building__name').annotate(
        count=Count('id')
    ).order_by('-count')
    
    # Get staff performance data
    staff_stats = requests.filter(
        assigned_to__isnull=False
    ).values('assigned_to__username').annotate(
        assigned_count=Count('id'),
        completed_count=Count('id', filter=Q(status='completed'))
    ).order_by('-assigned_count')
    
    # Add completion rate to staff stats
    for stat in staff_stats:
        if stat['assigned_count'] > 0:
            stat['completion_rate'] = (stat['completed_count'] / stat['assigned_count']) * 100
        else:
            stat['completion_rate'] = 0
    
    return render(request, 'view_report.html', {
        'report': report,
        'requests': requests[:30],  # Limit to first 30 for performance
        'category_stats': category_stats,
        'building_stats': building_stats,
        'staff_stats': staff_stats,
    })

@login_required
@staff_required
def view_inventory(request):
    """
    View maintenance inventory
    """
    inventory_items = InventoryItem.objects.all().order_by('name')
    
    # Pagination
    paginator = Paginator(inventory_items, 15)  # Show 15 items per page
    page_number = request.GET.get('page')
    paginated_items = paginator.get_page(page_number)
    
    # Count low stock and out of stock items
    low_stock_count = inventory_items.filter(quantity__gt=0, quantity__lte=5).count()
    out_of_stock_count = inventory_items.filter(quantity=0).count()
    
    return render(request, 'inventory.html', {
        'inventory_items': paginated_items,
        'low_stock_count': low_stock_count,
        'out_of_stock_count': out_of_stock_count,
        'total_items': inventory_items.count()
    })

@login_required
@admin_required
def add_inventory_item(request):
    """
    Add a new inventory item
    """
    if request.method == 'POST':
        form = InventoryItemForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Inventory item added successfully!')
            return redirect('inventory')  # Changed from 'view_inventory' to 'inventory'
    else:
        form = InventoryItemForm()
    
    return render(request, 'inventory_form.html', {
        'form': form,
        'title': 'Add Inventory Item',
        'button_text': 'Add Item'
    })

@login_required
@admin_required
def edit_inventory_item(request, item_id):
    """
    Edit an existing inventory item
    """
    item = get_object_or_404(InventoryItem, id=item_id)
    
    if request.method == 'POST':
        form = InventoryItemForm(request.POST, instance=item)
        if form.is_valid():
            form.save()
            messages.success(request, 'Inventory item updated successfully!')
            return redirect('inventory')  # Changed from 'view_inventory' to 'inventory'
    else:
        form = InventoryItemForm(instance=item)
    
    return render(request, 'inventory_form.html', {
        'form': form,
        'item': item,
        'title': 'Edit Inventory Item',
        'button_text': 'Save Changes'
    })

@login_required
@admin_required
def adjust_inventory_quantity(request, item_id):
    """
    Adjust quantity of an inventory item
    """
    item = get_object_or_404(InventoryItem, id=item_id)
    
    if request.method == 'POST':
        adjustment_type = request.POST.get('adjustmentType')  # Changed to match the form field name
        amount = int(request.POST.get('amount', 0))
        
        if adjustment_type == 'add':
            item.quantity += amount
        elif adjustment_type == 'remove':
            item.quantity = max(0, item.quantity - amount)
        
        item.save()
        messages.success(request, f'Inventory quantity adjusted successfully! New quantity: {item.quantity}')
        return redirect('inventory')  # Changed from 'view_inventory' to 'inventory'
    
    return render(request, 'adjust_inventory.html', {
        'item': item
    })


@login_required
@staff_required  # Allow both staff and admin (since admin passes the staff_required check)
def assign_request(request, request_id):
    """
    Allow staff to assign request to themselves or admin to assign to a specific staff
    """
    maintenance_request = get_object_or_404(MaintenanceRequest, id=request_id)
    
    if maintenance_request.assigned_to:
        messages.error(request, 'This request is already assigned')
        return redirect('view_maintenance_request', request_id=maintenance_request.id)
    
    if request.method == 'POST' and request.user.user_type == 'admin':
        # Admin is assigning to a specific staff member
        staff_id = request.POST.get('staff_id')
        if staff_id:
            staff_user = get_object_or_404(CustomUser, id=staff_id, user_type='staff')
            maintenance_request.assigned_to = staff_user
            assigner = request.user.username
        else:
            messages.error(request, 'No staff member selected')
            return redirect('view_maintenance_request', request_id=maintenance_request.id)
    else:
        # Staff is assigning to themselves
        maintenance_request.assigned_to = request.user
        assigner = request.user.username
    
    # Update request status and save
    maintenance_request.status = 'in_progress'
    maintenance_request.save()
    
    # Create a log entry
    assigned_to = maintenance_request.assigned_to.username
    MaintenanceLog.objects.create(
        request=maintenance_request,
        staff_member=request.user,
        description=f"Request assigned to {assigned_to} by {assigner}"
    )
    
    messages.success(request, f'Request successfully assigned to {assigned_to}')
    return redirect('view_maintenance_request', request_id=maintenance_request.id)


@login_required
@staff_required
def my_assigned_requests(request):
    """
    View for staff to see their assigned maintenance requests
    """
    assigned_requests = MaintenanceRequest.objects.filter(
        assigned_to=request.user
    ).select_related('category', 'building', 'requester').order_by('-created_at')
    
    # Filter by status if requested
    status_filter = request.GET.get('status')
    if status_filter:
        assigned_requests = assigned_requests.filter(status=status_filter)
    
    # Pagination
    paginator = Paginator(assigned_requests, 10)
    page_number = request.GET.get('page')
    paginated_requests = paginator.get_page(page_number)
    
    # Get counts by status
    status_counts = {
        'pending': assigned_requests.filter(status='pending').count(),
        'in_progress': assigned_requests.filter(status='in_progress').count(),
        'completed': assigned_requests.filter(status='completed').count(),
        'cancelled': assigned_requests.filter(status='cancelled').count(),
        'all': assigned_requests.count()
    }
    
    return render(request, 'my_assigned_requests.html', {
        'assigned_requests': paginated_requests,
        'status_counts': status_counts,
        'current_filter': status_filter or 'all'
    })

@login_required
@staff_required
def staff_request_pool(request):
    """
    View for staff to see all unassigned maintenance requests
    """
    unassigned_requests = MaintenanceRequest.objects.filter(
        assigned_to__isnull=True
    ).select_related('category', 'building', 'requester').order_by('created_at')
    
    # Filter by priority if requested
    priority_filter = request.GET.get('priority')
    if priority_filter:
        unassigned_requests = unassigned_requests.filter(priority=priority_filter)
    
    # Filter by category if requested
    category_filter = request.GET.get('category')
    if category_filter:
        unassigned_requests = unassigned_requests.filter(category__id=category_filter)
    
    # Pagination
    paginator = Paginator(unassigned_requests, 10)
    page_number = request.GET.get('page')
    paginated_requests = paginator.get_page(page_number)
    
    # Get categories for filter dropdown
    categories = MaintenanceCategory.objects.all()
    
    return render(request, 'staff_request_pool.html', {
        'unassigned_requests': paginated_requests,
        'categories': categories,
        'priority_filter': priority_filter,
        'category_filter': category_filter,
        'total_unassigned': unassigned_requests.count()
    })

# Add category and building management for admins
@login_required
@admin_required
def category_list(request):
    """
    View for admin to manage maintenance categories
    """
    categories = MaintenanceCategory.objects.all().order_by('name')
    
    return render(request, 'category_list.html', {
        'categories': categories
    })

@login_required
@admin_required
def add_category(request):
    """
    Add a new maintenance category
    """
    if request.method == 'POST':
        name = request.POST.get('name')
        description = request.POST.get('description', '')
        
        if not name:
            messages.error(request, 'Category name is required')
            return redirect('category_list')
        
        category = MaintenanceCategory.objects.create(
            name=name,
            description=description
        )
        
        messages.success(request, f'Category "{name}" created successfully!')
        return redirect('category_list')
    
    return render(request, 'add_category.html')

@login_required
@admin_required
def building_list(request):
    """
    View for admin to manage buildings
    """
    buildings = Building.objects.all().order_by('name')
    
    return render(request, 'building_list.html', {
        'buildings': buildings
    })

@login_required
@admin_required
def add_building(request):
    """
    Add a new building
    """
    if request.method == 'POST':
        name = request.POST.get('name')
        code = request.POST.get('code')
        address = request.POST.get('address', '')
        
        if not name or not code:
            messages.error(request, 'Building name and code are required')
            return redirect('building_list')
        
        building = Building.objects.create(
            name=name,
            code=code,
            address=address
        )
        
        messages.success(request, f'Building "{name}" created successfully!')
        return redirect('building_list')
    
    return render(request, 'add_building.html')