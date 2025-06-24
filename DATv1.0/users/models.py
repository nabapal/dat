from django.contrib.auth.models import AbstractUser
from django.db import models

# Create your models here.

class Team(models.Model):
    name = models.CharField(max_length=64, unique=True)
    description = models.CharField(max_length=255, blank=True, default='')

    def __str__(self):
        return self.name

class User(AbstractUser):
    role = models.CharField(max_length=32, default='member')
    is_active = models.BooleanField(default=False)
    teams = models.ManyToManyField(Team, related_name='users', blank=True)

    def __str__(self):
        return self.username
