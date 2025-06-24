from django import forms
from .models import Node, ActivityType, Status

class NodeForm(forms.ModelForm):
    class Meta:
        model = Node
        fields = ['name']

class ActivityTypeForm(forms.ModelForm):
    class Meta:
        model = ActivityType
        fields = ['name']

class StatusForm(forms.ModelForm):
    class Meta:
        model = Status
        fields = ['name', 'color']
