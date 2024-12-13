from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, authenticate, logout
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django.db.models import Count, Avg, Q
from django.utils import timezone

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
    UserRegistrationForm, 
    MaintenanceRequestForm, 
    MaintenanceLogForm, 
    MaintenanceReportForm
)

def home(request):
    """
    Home page view with an overview of maintenance requests
    """
    if not request.user.is_authenticated:
        return render(request, 'home.html')
    
    # Different dashboard views based on user type
    if request.user.user_type == 'student':
        # Fetch student's maintenance requests with additional details
        requests = MaintenanceRequest.objects.filter(requester=request.user).select_related(
            'category', 'building'
        ).order_by('-created_at')
        return render(request, 'student_dashboard.html', {
            'requests': requests
        })
    
    elif request.user.user_type == 'staff':
        # Fetch requests assigned to staff or unassigned
        assigned_requests = MaintenanceRequest.objects.filter(
            Q(assigned_to=request.user) | Q(assigned_to__isnull=True),
            status__in=['pending', 'in_progress']
        ).select_related('category', 'building')
        return render(request, 'staff_dashboard.html', {
            'assigned_requests': assigned_requests
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
            'requester', 'category'
        ).order_by('-created_at')[:10]
        
        # Additional metrics
        metrics = {
            'total_users': CustomUser.objects.count(),
            'total_buildings': Building.objects.count(),
            'total_categories': MaintenanceCategory.objects.count(),
            'pending_requests': total_requests.filter(status='pending').count(),
            'in_progress_requests': total_requests.filter(status='in_progress').count(),
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
    if request.method == 'POST':
        username = request.POST['username']
        password = request.POST['password']
        user = authenticate(request, username=username, password=password)
        
        if user is not None:
            login(request, user)
            messages.success(request, 'Login successful!')
            return redirect('home')
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

def user_registration(request):
    """
    User registration view
    """
    if request.method == 'POST':
        form = UserRegistrationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            messages.success(request, 'Registration successful!')
            return redirect('home')
    else:
        form = UserRegistrationForm()
    
    return render(request, 'registration.html', {'form': form})

@login_required
def create_maintenance_request(request):
    """
    View for creating a new maintenance request
    """
    if request.method == 'POST':
        form = MaintenanceRequestForm(request.POST)
        if form.is_valid():
            maintenance_request = form.save(commit=False)
            maintenance_request.requester = request.user
            maintenance_request.save()
            messages.success(request, 'Maintenance request submitted successfully!')
            return redirect('home')
    else:
        form = MaintenanceRequestForm()
    
    return render(request, 'create_request.html', {'form': form})

@login_required
def view_maintenance_request(request, request_id):
    """
    View details of a specific maintenance request
    """
    maintenance_request = get_object_or_404(
        MaintenanceRequest, 
        id=request_id
    )
    
    # Check user permissions
    if (request.user.user_type == 'student' and 
        maintenance_request.requester != request.user):
        messages.error(request, 'You are not authorized to view this request')
        return redirect('home')
    
    logs = MaintenanceLog.objects.filter(request=maintenance_request)
    
    return render(request, 'request_detail.html', {
        'request': maintenance_request,
        'logs': logs
    })

@login_required
def update_maintenance_request(request, request_id):
    """
    Update status of a maintenance request
    """
    maintenance_request = get_object_or_404(
        MaintenanceRequest, 
        id=request_id
    )
    
    # Only staff and admin can update requests
    if request.user.user_type not in ['staff', 'admin']:
        messages.error(request, 'You are not authorized to update this request')
        return redirect('home')
    
    if request.method == 'POST':
        # Update request status and log the update
        maintenance_request.status = request.POST.get('status')
        maintenance_request.save()
        
        log = MaintenanceLog.objects.create(
            request=maintenance_request,
            staff_member=request.user,
            description=request.POST.get('log_description', '')
        )
        
        messages.success(request, 'Request updated successfully!')
        return redirect('view_maintenance_request', request_id=maintenance_request.id)
    
    return render(request, 'update_request.html', {
        'request': maintenance_request
    })

@user_passes_test(lambda u: u.user_type == 'admin')
def generate_maintenance_report(request):
    """
    Generate maintenance performance report
    """
    if request.method == 'POST':
        form = MaintenanceReportForm(request.POST)
        if form.is_valid():
            start_date = form.cleaned_data['start_date']
            end_date = form.cleaned_data['end_date']
            
            requests = MaintenanceRequest.objects.filter(
                created_at__range=[start_date, end_date]
            )
            
            report = MaintenanceReport.objects.create(
                generated_by=request.user,
                start_date=start_date,
                end_date=end_date,
                total_requests=requests.count(),
                completed_requests=requests.filter(status='completed').count(),
                average_resolution_time=requests.aggregate(
                    Avg('updated_at' - 'created_at')
                )['updated_at__avg'] or 0
            )
            
            messages.success(request, 'Report generated successfully!')
            return redirect('view_report', report_id=report.id)
    else:
        form = MaintenanceReportForm()
    
    return render(request, 'generate_report.html', {'form': form})



@login_required
def view_inventory(request):
    """
    View maintenance inventory
    """
    if request.user.user_type not in ['staff', 'admin']:
        messages.error(request, 'You are not authorized to view inventory')
        return redirect('home')
    
    inventory_items = InventoryItem.objects.all()
    return render(request, 'inventory.html', {
        'inventory_items': inventory_items
    })

@login_required
def assign_request(request, request_id):
    """
    Allow staff to assign a maintenance request to themselves
    """
    if request.user.user_type not in ['staff', 'admin']:
        messages.error(request, 'You are not authorized to assign requests')
        return redirect('home')
    
    maintenance_request = get_object_or_404(MaintenanceRequest, id=request_id)
    
    if maintenance_request.assigned_to:
        messages.error(request, 'This request is already assigned')
        return redirect('staff_request_pool')
    
    maintenance_request.assigned_to = request.user
    maintenance_request.status = 'in_progress'
    maintenance_request.save()
    
    # Create a log entry
    MaintenanceLog.objects.create(
        request=maintenance_request,
        staff_member=request.user,
        description=f"Request assigned to {request.user.username}"
    )
    
    messages.success(request, 'Request successfully assigned')
    return redirect('view_maintenance_request', request_id=maintenance_request.id)

@login_required
def my_assigned_requests(request):
    """
    View for staff to see their assigned maintenance requests
    """
    if request.user.user_type not in ['staff', 'admin']:
        messages.error(request, 'You are not authorized to view this page')
        return redirect('home')
    
    assigned_requests = MaintenanceRequest.objects.filter(
        assigned_to=request.user
    ).order_by('-created_at')
    
    return render(request, 'my_assigned_requests.html', {
        'assigned_requests': assigned_requests
    })

@login_required
def staff_request_pool(request):
    """
    View for staff to see all unassigned maintenance requests
    """
    if request.user.user_type not in ['staff', 'admin']:
        messages.error(request, 'You are not authorized to view this page')
        return redirect('home')
    
    unassigned_requests = MaintenanceRequest.objects.filter(
        assigned_to__isnull=True
    ).order_by('created_at')
    
    return render(request, 'staff_request_pool.html', {
        'unassigned_requests': unassigned_requests
    })

