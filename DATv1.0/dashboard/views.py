from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from activities.models import Activity
from users.models import Team, User

# Create your views here.

@login_required
def dashboard_view(request):
    total_activities = Activity.objects.count()
    total_teams = Team.objects.count()
    total_users = User.objects.count()
    return render(request, 'dashboard/dashboard.html', {
        'total_activities': total_activities,
        'total_teams': total_teams,
        'total_users': total_users,
    })
