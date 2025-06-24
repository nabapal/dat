from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect, get_object_or_404
from .models import Activity, ActivityUpdate
from .forms import ActivityForm, ActivityUpdateForm

@login_required
def activity_list(request):
    activities = Activity.objects.all()
    return render(request, 'activities/activity_list.html', {'activities': activities})

@login_required
def activity_create(request):
    if request.method == 'POST':
        form = ActivityForm(request.POST)
        if form.is_valid():
            activity = form.save(commit=False)
            activity.user = request.user
            activity.assigner = request.user
            activity.save()
            form.save_m2m()
            return redirect('activity_list')
    else:
        form = ActivityForm()
    return render(request, 'activities/activity_form.html', {'form': form})

@login_required
def activity_edit(request, pk):
    activity = get_object_or_404(Activity, pk=pk)
    if request.method == 'POST':
        form = ActivityForm(request.POST, instance=activity)
        if form.is_valid():
            form.save()
            return redirect('activity_list')
    else:
        form = ActivityForm(instance=activity)
    return render(request, 'activities/activity_form.html', {'form': form, 'edit': True})

@login_required
def activity_delete(request, pk):
    activity = get_object_or_404(Activity, pk=pk)
    if request.method == 'POST':
        activity.delete()
        return redirect('activity_list')
    return render(request, 'activities/activity_confirm_delete.html', {'activity': activity})

@login_required
def activity_updates(request, pk):
    activity = get_object_or_404(Activity, pk=pk)
    updates = ActivityUpdate.objects.filter(activity=activity)
    if request.method == 'POST':
        form = ActivityUpdateForm(request.POST)
        if form.is_valid():
            update = form.save(commit=False)
            update.activity = activity
            update.updated_by = request.user
            update.save()
            return redirect('activity_updates', pk=activity.pk)
    else:
        form = ActivityUpdateForm()
    return render(request, 'activities/activity_updates.html', {'activity': activity, 'updates': updates, 'form': form})
