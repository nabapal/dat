from django.urls import path
from . import views

urlpatterns = [
    path('', views.team_list, name='team_list'),
    path('create/', views.team_create, name='team_create'),
    path('<int:pk>/edit/', views.team_edit, name='team_edit'),
    path('<int:pk>/delete/', views.team_delete, name='team_delete'),
]
