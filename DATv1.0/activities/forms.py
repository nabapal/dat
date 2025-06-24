from django import forms
from .models import Activity, ActivityUpdate

class ActivityForm(forms.ModelForm):
    class Meta:
        model = Activity
        fields = [
            'activity_id', 'details', 'node_name', 'activity_type', 'status',
            'start_date', 'end_date', 'duration', 'assignees', 'team'
        ]
        widgets = {
            'start_date': forms.DateTimeInput(attrs={'type': 'datetime-local'}),
            'end_date': forms.DateTimeInput(attrs={'type': 'datetime-local'}),
            'assignees': forms.CheckboxSelectMultiple,
        }

class ActivityUpdateForm(forms.ModelForm):
    class Meta:
        model = ActivityUpdate
        fields = ['update_date', 'update_text']
        widgets = {
            'update_date': forms.DateInput(attrs={'type': 'date'}),
        }
