from django import forms
from django.contrib.auth.forms import UserCreationForm
from .models import (
    CustomUser, 
    MaintenanceRequest, 
    MaintenanceReport,
    MaintenanceCategory,
    MaintenanceLog,
    Building
)
class UserRegistrationForm(UserCreationForm):
    """
    Extended user registration form with additional fields
    """
    class Meta:
        model = CustomUser
        fields = [
            'username', 
            'email', 
            'password1', 
            'password2', 
            'user_type', 
            'department', 
            'contact_number'
        ]
        widgets = {
            'user_type': forms.Select(attrs={'class': 'form-control'}),
        }
class MaintenanceRequestForm(forms.ModelForm):
    """
    Form for creating maintenance requests with enhanced validation
    """
    category = forms.ModelChoiceField(
        queryset=MaintenanceCategory.objects.all(), 
        empty_label="Select Category"
    )
    
    building = forms.ModelChoiceField(
        queryset=Building.objects.all(), 
        empty_label="Select Building"
    )

    class Meta:
        model = MaintenanceRequest
        fields = [
            'category', 
            'building', 
            'room_number', 
            'title', 
            'description', 
            'priority'
        ]
        widgets = {
            'description': forms.Textarea(attrs={'rows': 4}),
            'priority': forms.Select(attrs={'class': 'form-control'}),
        }

    def clean_title(self):
        """
        Validate title length
        """
        title = self.cleaned_data['title']
        if len(title) < 5:
            raise forms.ValidationError("Title must be at least 5 characters long")
        return title

class MaintenanceLogForm(forms.ModelForm):
    """
    Form for logging maintenance work progress
    """
    class Meta:
        model = MaintenanceLog
        fields = ['description']

class MaintenanceReportForm(forms.Form):
    """
    Form for generating maintenance reports
    """
    start_date = forms.DateField(
        widget=forms.DateInput(attrs={'type': 'date'})
    )
    end_date = forms.DateField(
        widget=forms.DateInput(attrs={'type': 'date'})
    )