from django.db import models
from django.contrib.auth.models import AbstractUser
from django.utils import timezone

class CustomUser(AbstractUser):
    """
    Extended User model to support different user types
    """
    USER_TYPE_CHOICES = (
        ('student', 'Student'),
        ('staff', 'Staff'),
        ('admin', 'Administrator'),
    )
    
    user_type = models.CharField(max_length=10, choices=USER_TYPE_CHOICES)
    department = models.CharField(max_length=100, blank=True, null=True)
    contact_number = models.CharField(max_length=15, blank=True, null=True)
    
    def __str__(self):
        return f"{self.username} - {self.get_user_type_display()}"

class Building(models.Model):
    """
    Represents buildings or locations within the college
    """
    name = models.CharField(max_length=100)
    code = models.CharField(max_length=10, unique=True)
    address = models.TextField(blank=True)
    
    def __str__(self):
        return self.name

class MaintenanceCategory(models.Model):
    """
    Maintenance request categories
    """
    name = models.CharField(max_length=50, unique=True)
    description = models.TextField(blank=True)
    
    def __str__(self):
        return self.name

class MaintenanceRequest(models.Model):
    """
    Maintenance request model to track service requests
    """
    STATUS_CHOICES = (
        ('pending', 'Pending'),
        ('in_progress', 'In Progress'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
    )
    
    PRIORITY_CHOICES = (
        ('low', 'Low'),
        ('medium', 'Medium'),
        ('high', 'High'),
        ('urgent', 'Urgent'),
    )
    
    requester = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='requests')
    category = models.ForeignKey(MaintenanceCategory, on_delete=models.SET_NULL, null=True)
    building = models.ForeignKey(Building, on_delete=models.SET_NULL, null=True)
    
    title = models.CharField(max_length=200)
    description = models.TextField()
    
    room_number = models.CharField(max_length=50, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    priority = models.CharField(max_length=10, choices=PRIORITY_CHOICES, default='medium')
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    assigned_to = models.ForeignKey(CustomUser, on_delete=models.SET_NULL, 
                                    null=True, 
                                    related_name='assigned_requests', 
                                    blank=True)
    
    def __str__(self):
        return f"{self.title} - {self.get_status_display()}"

class MaintenanceLog(models.Model):
    """
    Tracks work progress and updates for maintenance requests
    """
    request = models.ForeignKey(MaintenanceRequest, on_delete=models.CASCADE, related_name='logs')
    staff_member = models.ForeignKey(CustomUser, on_delete=models.CASCADE)
    
    description = models.TextField()
    timestamp = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"Log for {self.request.title} by {self.staff_member.username}"

class InventoryItem(models.Model):
    """
    Tracks maintenance supplies and equipment
    """
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    quantity = models.PositiveIntegerField(default=0)
    
    def __str__(self):
        return f"{self.name} (Qty: {self.quantity})"

class MaintenanceReport(models.Model):
    """
    Generates performance and analysis reports
    """
    generated_by = models.ForeignKey(CustomUser, on_delete=models.CASCADE)
    generated_at = models.DateTimeField(auto_now_add=True)
    
    start_date = models.DateField()
    end_date = models.DateField()
    
    total_requests = models.IntegerField()
    completed_requests = models.IntegerField()
    average_resolution_time = models.FloatField()  # in hours
    
    report_file = models.FileField(upload_to='maintenance_reports/', blank=True)
    
    def __str__(self):
        return f"Report {self.start_date} to {self.end_date}"