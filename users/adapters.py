from allauth.account.adapter import DefaultAccountAdapter
from allauth.socialaccount.adapter import DefaultSocialAccountAdapter
from allauth.account.utils import user_email
from django.conf import settings


class CustomAccountAdapter(DefaultAccountAdapter):
    """Custom account adapter to handle user creation without username."""
    
    def save_user(self, request, user, form, commit=True):
        """Save user without username field."""
        data = form.cleaned_data
        user_email(user, data.get('email'))
        user.first_name = data.get('first_name', '')
        user.last_name = data.get('last_name', '')
        if 'password1' in data:
            user.set_password(data['password1'])
        else:
            user.set_unusable_password()
        if commit:
            user.save()
        return user


class CustomSocialAccountAdapter(DefaultSocialAccountAdapter):
    """Custom social account adapter to handle social login data."""
    
    def populate_user(self, request, sociallogin, data):
        """Populate user data from social provider."""
        user = sociallogin.user
        user.email = data.get('email', '')
        user.first_name = data.get('first_name', '')
        user.last_name = data.get('last_name', '')
        return user
    
    def save_user(self, request, sociallogin, form=None):
        """Save user from social login."""
        user = super().save_user(request, sociallogin, form)
        # Additional processing if needed
        return user
