from django.conf import settings
from django.db import models
from users.models import Team, User

# Create your models here.

class Node(models.Model):
    name = models.CharField(max_length=50, unique=True)
    def __str__(self):
        return self.name

class ActivityType(models.Model):
    name = models.CharField(max_length=50, unique=True)
    def __str__(self):
        return self.name

class Status(models.Model):
    name = models.CharField(max_length=50, unique=True)
    color = models.CharField(max_length=20, default='secondary')
    def __str__(self):
        return self.name
