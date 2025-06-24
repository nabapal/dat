from django.urls import path
from . import views

urlpatterns = [
    path('manage/', views.attributes_manage, name='attributes_manage'),
    # Node URLs
    path('nodes/', views.node_list, name='node_list'),
    path('nodes/create/', views.node_create, name='node_create'),
    path('nodes/<int:pk>/edit/', views.node_edit, name='node_edit'),
    path('nodes/<int:pk>/delete/', views.node_delete, name='node_delete'),
    # ActivityType URLs
    path('activitytypes/', views.activitytype_list, name='activitytype_list'),
    path('activitytypes/create/', views.activitytype_create, name='activitytype_create'),
    path('activitytypes/<int:pk>/edit/', views.activitytype_edit, name='activitytype_edit'),
    path('activitytypes/<int:pk>/delete/', views.activitytype_delete, name='activitytype_delete'),
    # Status URLs
    path('statuses/', views.status_list, name='status_list'),
    path('statuses/create/', views.status_create, name='status_create'),
    path('statuses/<int:pk>/edit/', views.status_edit, name='status_edit'),
    path('statuses/<int:pk>/delete/', views.status_delete, name='status_delete'),
]
