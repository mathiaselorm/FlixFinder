from django import forms
from django.contrib.auth.forms import UserCreationForm, UserChangeForm
from django.contrib.auth import get_user_model
from django.utils.translation import gettext_lazy as _
from django.core.exceptions import ValidationError

CustomUser = get_user_model()

class CustomUserCreationForm(UserCreationForm):
    """
    A form for creating new users. Includes all the required
    fields, plus a repeated password.
    """
    class Meta(UserCreationForm.Meta):
        model = CustomUser
        fields = (
            'first_name', 
            'last_name', 
            'email', 
            'is_staff', 
            'is_active', 
            'is_superuser'
        )
        labels = {
            'first_name': _('First Name'),
            'last_name': _('Last Name'),
            'email': _('Email Address'),
            'is_active': _('Active'),
            'is_staff': _('Staff Status'),
            'is_superuser': _('Superuser Status')
        }

    def clean_email(self):
        """
        Validate that the supplied email address is unique for the site.
        """
        email = self.cleaned_data['email']
        if CustomUser.objects.filter(email=email).exists():
            raise ValidationError(_("A user with that email already exists."))
        return email

    def save(self, commit=True):
        """
        Save the provided password in hashed format
        """
        user = super().save(commit=False)
        user.set_password(self.cleaned_data["password1"])
        if commit:
            user.save()
        return user


class CustomUserChangeForm(UserChangeForm):
    """
    A form for updating users. Includes all the fields on
    the user, but replaces the password field with admin's
    password hash display field.
    """
    class Meta(UserChangeForm.Meta):
        model = CustomUser
        fields = (
            'first_name', 
            'last_name', 
            'email', 
            'is_staff', 
            'is_active', 
            'is_superuser'
        )
        labels = {
            'email': _('Email Address'),
            'first_name': _('First Name'),
            'last_name': _('Last Name'),
            'is_active': _('Active'),
            'is_staff': _('Staff Status'),
            'is_superuser': _('Superuser Status'),
            'groups': _('Groups'),
            'user_permissions': _('User Permissions'),
        }
        help_texts = {
            'is_active': _('Designates whether this user should be treated as active. Unselect this instead of deleting accounts.'),
            'is_staff': _('Designates whether the user can log into this admin site.'),
        }

