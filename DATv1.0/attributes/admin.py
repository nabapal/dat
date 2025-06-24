from django.contrib import admin
from .models import Node, ActivityType, Status

# Register your models here.
admin.site.register(Node)
admin.site.register(ActivityType)
admin.site.register(Status)
