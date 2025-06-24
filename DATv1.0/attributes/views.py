from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect, get_object_or_404
from .models import Node, ActivityType, Status
from .forms import NodeForm, ActivityTypeForm, StatusForm

# Node Views
@login_required
def node_list(request):
    nodes = Node.objects.all()
    return render(request, 'attributes/node_list.html', {'nodes': nodes})

@login_required
def node_create(request):
    if request.method == 'POST':
        form = NodeForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect('node_list')
    else:
        form = NodeForm()
    return render(request, 'attributes/node_form.html', {'form': form})

@login_required
def node_edit(request, pk):
    node = get_object_or_404(Node, pk=pk)
    if request.method == 'POST':
        form = NodeForm(request.POST, instance=node)
        if form.is_valid():
            form.save()
            return redirect('node_list')
    else:
        form = NodeForm(instance=node)
    return render(request, 'attributes/node_form.html', {'form': form, 'edit': True})

@login_required
def node_delete(request, pk):
    node = get_object_or_404(Node, pk=pk)
    if request.method == 'POST':
        node.delete()
        return redirect('node_list')
    return render(request, 'attributes/node_confirm_delete.html', {'node': node})

# ActivityType Views
@login_required
def activitytype_list(request):
    types = ActivityType.objects.all()
    return render(request, 'attributes/activitytype_list.html', {'types': types})

@login_required
def activitytype_create(request):
    if request.method == 'POST':
        form = ActivityTypeForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect('activitytype_list')
    else:
        form = ActivityTypeForm()
    return render(request, 'attributes/activitytype_form.html', {'form': form})

@login_required
def activitytype_edit(request, pk):
    activitytype = get_object_or_404(ActivityType, pk=pk)
    if request.method == 'POST':
        form = ActivityTypeForm(request.POST, instance=activitytype)
        if form.is_valid():
            form.save()
            return redirect('activitytype_list')
    else:
        form = ActivityTypeForm(instance=activitytype)
    return render(request, 'attributes/activitytype_form.html', {'form': form, 'edit': True})

@login_required
def activitytype_delete(request, pk):
    activitytype = get_object_or_404(ActivityType, pk=pk)
    if request.method == 'POST':
        activitytype.delete()
        return redirect('activitytype_list')
    return render(request, 'attributes/activitytype_confirm_delete.html', {'activitytype': activitytype})

# Status Views
@login_required
def status_list(request):
    statuses = Status.objects.all()
    return render(request, 'attributes/status_list.html', {'statuses': statuses})

@login_required
def status_create(request):
    if request.method == 'POST':
        form = StatusForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect('status_list')
    else:
        form = StatusForm()
    return render(request, 'attributes/status_form.html', {'form': form})

@login_required
def status_edit(request, pk):
    status = get_object_or_404(Status, pk=pk)
    if request.method == 'POST':
        form = StatusForm(request.POST, instance=status)
        if form.is_valid():
            form.save()
            return redirect('status_list')
    else:
        form = StatusForm(instance=status)
    return render(request, 'attributes/status_form.html', {'form': form, 'edit': True})

@login_required
def status_delete(request, pk):
    status = get_object_or_404(Status, pk=pk)
    if request.method == 'POST':
        status.delete()
        return redirect('status_list')
    return render(request, 'attributes/status_confirm_delete.html', {'status': status})

# Combined Attributes Manage View
@login_required
def attributes_manage(request):
    nodes = Node.objects.all()
    types = ActivityType.objects.all()
    statuses = Status.objects.all()
    node_form = NodeForm(prefix='node')
    activitytype_form = ActivityTypeForm(prefix='type')
    status_form = StatusForm(prefix='status')
    # Handle create POSTs for each form
    if request.method == 'POST':
        if 'node-name' in request.POST:
            node_form = NodeForm(request.POST, prefix='node')
            if node_form.is_valid():
                node_form.save()
                return redirect('attributes_manage')
        elif 'type-name' in request.POST:
            activitytype_form = ActivityTypeForm(request.POST, prefix='type')
            if activitytype_form.is_valid():
                activitytype_form.save()
                return redirect('attributes_manage')
        elif 'status-name' in request.POST:
            status_form = StatusForm(request.POST, prefix='status')
            if status_form.is_valid():
                status_form.save()
                return redirect('attributes_manage')
    return render(request, 'attributes/attributes_manage.html', {
        'nodes': nodes,
        'types': types,
        'statuses': statuses,
        'node_form': node_form,
        'activitytype_form': activitytype_form,
        'status_form': status_form,
    })
