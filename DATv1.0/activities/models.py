from django.db import models
from users.models import User, Team
from datetime import date
from attributes.models import Node, ActivityType, Status

class Activity(models.Model):
    activity_id = models.CharField(max_length=20, unique=True)
    details = models.TextField()
    node_name = models.ForeignKey(Node, on_delete=models.SET_NULL, null=True, blank=True)
    activity_type = models.ForeignKey(ActivityType, on_delete=models.SET_NULL, null=True, blank=True)
    status = models.ForeignKey(Status, on_delete=models.SET_NULL, null=True, blank=True, default=None)
    start_date = models.DateTimeField()
    end_date = models.DateTimeField(null=True, blank=True)
    duration = models.FloatField(null=True, blank=True)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='created_activities')
    assigner = models.ForeignKey(User, on_delete=models.CASCADE, related_name='assigned_activities')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    assignees = models.ManyToManyField(User, related_name='assigned_activities_set', blank=True)
    team = models.ForeignKey(Team, on_delete=models.SET_NULL, null=True, blank=True)

    def __str__(self):
        return self.activity_id

    @property
    def age_days(self):
        """Return aging in days between start_date and end_date (or today if end_date is None)."""
        if not self.start_date:
            return None
        start = self.start_date.date()
        end = self.end_date.date() if self.end_date else date.today()
        return (end - start).days

class ActivityUpdate(models.Model):
    activity = models.ForeignKey(Activity, on_delete=models.CASCADE)
    update_date = models.DateField()
    update_text = models.TextField()
    updated_by = models.ForeignKey(User, on_delete=models.CASCADE)

    def __str__(self):
        return f"Update for {self.activity.activity_id} on {self.update_date}"
