from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.core.validators import RegexValidator
from .models import (
    CustomUser, 
    MaintenanceRequest, 
    MaintenanceReport,
    MaintenanceCategory,
    MaintenanceLog,
    Building,InventoryItem
)

# Phone number validator
phone_validator = RegexValidator(
    regex=r'^\d{10}$',
    message='Phone number must be exactly 10 digits',
    code='invalid_phone'
)

class UserRegistrationForm(UserCreationForm):
    """
    Extended user registration form with additional fields
    """
    # Add phone validation to contact_number
    contact_number = forms.CharField(
        required=False,
        validators=[phone_validator],
        widget=forms.TextInput(attrs={'placeholder': 'Enter 10-digit phone number'})
    )
    
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


class InventoryItemForm(forms.ModelForm):
    class Meta:
        model = InventoryItem
        fields = ['name', 'description', 'quantity']
        widgets = {
            'description': forms.Textarea(attrs={'rows': 3}),
        }


# Updated forms below

class UserCreationForm(forms.ModelForm):
    """
    Form for admin to create a new user
    """
    password1 = forms.CharField(label='Password', widget=forms.PasswordInput)
    password2 = forms.CharField(label='Confirm Password', widget=forms.PasswordInput)
    
    # Add phone validation to contact_number
    contact_number = forms.CharField(
        required=False,
        validators=[phone_validator],
        widget=forms.TextInput(attrs={'placeholder': 'Enter 10-digit phone number'})
    )
    
    class Meta:
        model = CustomUser
        fields = ['username', 'email', 'user_type', 'department', 'contact_number']
        widgets = {
            'user_type': forms.Select(attrs={'class': 'form-control'}),
        }
    
    def clean_password2(self):
        password1 = self.cleaned_data.get('password1')
        password2 = self.cleaned_data.get('password2')
        if password1 and password2 and password1 != password2:
            raise forms.ValidationError("Passwords don't match")
        return password2
    
    def save(self, commit=True):
        user = super().save(commit=False)
        user.set_password(self.cleaned_data['password1'])
        if commit:
            user.save()
        return user

class UserEditForm(forms.ModelForm):
    """
    Form for admin to edit an existing user
    """
    # Add phone validation to contact_number
    contact_number = forms.CharField(
        required=False,
        validators=[phone_validator],
        widget=forms.TextInput(attrs={'placeholder': 'Enter 10-digit phone number'})
    )
    
    class Meta:
        model = CustomUser
        fields = ['username', 'email', 'user_type', 'department', 'contact_number', 'is_active']
        widgets = {
            'user_type': forms.Select(attrs={'class': 'form-control'}),
        }