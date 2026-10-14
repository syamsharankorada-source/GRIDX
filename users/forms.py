from django import forms
from django.contrib.auth.models import User
from .models import CustomerProfile, ProviderProfile, Vehicle
from services.models import ServiceCategory

class StyledFormMixin:
    def _style_fields(self):
        for name, field in self.fields.items():
            if isinstance(field.widget, forms.CheckboxSelectMultiple):
                field.widget.attrs.update({'class': 'gridx-checkbox-list'})
            elif isinstance(field.widget, forms.Select):
                field.widget.attrs.update({'class': 'form-select gridx-input'})
            else:
                field.widget.attrs.update({'class': 'form-control gridx-input'})

class CustomerRegistrationForm(StyledFormMixin, forms.ModelForm):
    password = forms.CharField(widget=forms.PasswordInput(attrs={'placeholder': 'Create strong password'}))
    phone = forms.CharField(max_length=20, initial='9848012345', widget=forms.TextInput(attrs={'placeholder': '+91 98480 12345'}))
    vehicle_type = forms.ChoiceField(choices=Vehicle.VEHICLE_TYPES, initial='CAR')
    make_model = forms.CharField(max_length=100, initial='Hyundai Creta SX', widget=forms.TextInput(attrs={'placeholder': 'e.g. Hyundai Creta / Honda Activa'}))
    registration_number = forms.CharField(max_length=30, initial='AP 16 DX 2026', widget=forms.TextInput(attrs={'placeholder': 'e.g. AP 16 DX 2026'}))

    class Meta:
        model = User
        fields = ['username', 'email', 'password']
        widgets = {
            'username': forms.TextInput(attrs={'placeholder': 'Choose a username'}),
            'email': forms.EmailInput(attrs={'placeholder': 'you@example.com'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._style_fields()

    def save(self, commit=True):
        user = super().save(commit=False)
        user.set_password(self.cleaned_data['password'])
        if commit:
            user.save()
            CustomerProfile.objects.create(user=user, phone=self.cleaned_data['phone'])
            Vehicle.objects.create(
                owner=user,
                vehicle_type=self.cleaned_data['vehicle_type'],
                make_model=self.cleaned_data['make_model'],
                registration_number=self.cleaned_data['registration_number']
            )
        return user

class ProviderRegistrationForm(StyledFormMixin, forms.ModelForm):
    password = forms.CharField(widget=forms.PasswordInput(attrs={'placeholder': 'Create strong password'}))
    phone = forms.CharField(max_length=20, initial='9848099999')
    business_name = forms.CharField(max_length=120, initial='Vijayawada Rapid Roadside & Home Pro')
    service_radius_km = forms.FloatField(initial=20.0)
    supported_vehicles = forms.CharField(initial="BIKE,CAR,SUV,EV,HOME")
    skills = forms.ModelMultipleChoiceField(
        queryset=ServiceCategory.objects.all(),
        widget=forms.CheckboxSelectMultiple,
        required=False
    )

    class Meta:
        model = User
        fields = ['username', 'email', 'password']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._style_fields()

    def save(self, commit=True):
        user = super().save(commit=False)
        user.set_password(self.cleaned_data['password'])
        if commit:
            user.save()
            profile = ProviderProfile.objects.create(
                user=user,
                phone=self.cleaned_data['phone'],
                business_name=self.cleaned_data['business_name'],
                service_radius_km=self.cleaned_data['service_radius_km'],
                supported_vehicles=self.cleaned_data['supported_vehicles'],
                is_verified=True
            )
            if self.cleaned_data.get('skills'):
                profile.skills.set(self.cleaned_data['skills'])
            else:
                profile.skills.set(ServiceCategory.objects.all())
        return user

class VehicleForm(StyledFormMixin, forms.ModelForm):
    class Meta:
        model = Vehicle
        fields = ['vehicle_type', 'make_model', 'registration_number']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._style_fields()
