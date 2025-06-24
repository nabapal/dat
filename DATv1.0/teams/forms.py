from django import forms
from users.models import Team

class TeamForm(forms.ModelForm):
    class Meta:
        model = Team
        fields = ['name']
