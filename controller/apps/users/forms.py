from django import forms
from django.contrib.auth.forms import ReadOnlyPasswordHashField
from django.core.exceptions import ValidationError

from common.fields import MultiSelectFormField

from users.models import User, JoinRequest


class UserCreationForm(forms.ModelForm):
    password1 = forms.CharField(label='Password', widget=forms.PasswordInput)
    password2 = forms.CharField(label='Password confirmation', widget=forms.PasswordInput)
    
    class Meta:
        model = User
        fields = ('username', 'email')
    
    def clean_password2(self):
        # Check that the two password entries match
        password1 = self.cleaned_data.get("password1")
        password2 = self.cleaned_data.get("password2")
        if password1 and password2 and password1 != password2:
            raise forms.ValidationError("Passwords don't match")
        return password2
    
    def save(self, commit=True):
        # Save the provided password in hashed format
        user = super(UserCreationForm, self).save(commit=False)
        user.set_password(self.cleaned_data["password1"])
        if commit:
            user.save()
        return user


class UserChangeForm(forms.ModelForm):
    password = ReadOnlyPasswordHashField()
    
    class Meta:
        model = User
    
    def clean_password(self):
        # Regardless of what the user provides, return the initial value.
        # This is done here, rather than on the field, because the
        # field does not have access to the initial value
        return self.initial["password"]


class JoinRequestForm(forms.ModelForm):
    ACTIONS = (
        (None, '------'),
        ('accept', 'Accept'),
        ('reject', 'Reject'))
    ROLES = (
        ('researcher', 'Researcher'),
        ('admin', 'Admin'),
        ('technician', 'Technician'))
    
    action = forms.ChoiceField(label='Action', choices=ACTIONS, required=False)
    roles = MultiSelectFormField(label='Roles', choices=ROLES, required=False)
    
    class Meta:
        model = JoinRequest
    
    def save(self, commit=True):
        action = self.cleaned_data.get('action')
        if action == 'accept':
            roles = self.cleaned_data.get('roles')
            self.instance.accept(roles=roles)
        elif action == 'reject':
            self.instance.reject()