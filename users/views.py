from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, logout
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from .forms import CustomerRegistrationForm, ProviderRegistrationForm, VehicleForm
from .models import Vehicle
from services.views import ensure_seed_catalog

def register_view(request):
    ensure_seed_catalog()
    role = request.GET.get('role', 'customer')
    if request.method == 'POST':
        role = request.POST.get('role', 'customer')
        form = ProviderRegistrationForm(request.POST) if role == 'provider' else CustomerRegistrationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            messages.success(request, f"Welcome to GRIDX, {user.username}! Your account is active.")
            return redirect('provider_dashboard' if hasattr(user, 'provider_profile') else 'dashboard')
    else:
        form = ProviderRegistrationForm() if role == 'provider' else CustomerRegistrationForm()
    return render(request, 'pages/register.html', {'form': form, 'role': role})

def login_view(request):
    ensure_seed_catalog()
    if request.method == 'POST':
        form = AuthenticationForm(request, data=request.POST)
        if form.is_valid():
            user = form.get_user()
            login(request, user)
            messages.success(request, f"Signed in as {user.username}.")
            return redirect('provider_dashboard' if hasattr(user, 'provider_profile') else 'dashboard')
        else:
            messages.error(request, "Invalid username or password. Try demo: ravi_mech / gridxpassword123")
    else:
        form = AuthenticationForm()
    for field in form.fields.values():
        field.widget.attrs.update({'class': 'form-control gridx-input'})
    return render(request, 'pages/login.html', {'form': form})

def logout_view(request):
    logout(request)
    messages.info(request, "You have been logged out safely.")
    return redirect('home')

@login_required
def add_vehicle_view(request):
    if request.method == 'POST':
        form = VehicleForm(request.POST)
        if form.is_valid():
            v = form.save(commit=False)
            v.owner = request.user
            v.save()
            messages.success(request, f"Added {v.make_model} ({v.registration_number}) to your garage.")
    return redirect('dashboard')

@login_required
def delete_vehicle_view(request, vehicle_id):
    v = get_object_or_404(Vehicle, id=vehicle_id, owner=request.user)
    if request.user.vehicles.count() > 1:
        v.delete()
        messages.info(request, "Vehicle removed.")
    else:
        messages.warning(request, "Keep at least one active vehicle/unit in your profile.")
    return redirect('dashboard')
