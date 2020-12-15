from django import forms
from django.contrib.auth.models import User
from django.contrib.auth.forms import UserCreationForm, get_user_model


class UserForm(forms.ModelForm):
    class Meta(UserCreationForm.Meta):
        model = User
        fields = ('email','username','password')
        widgets = {
            'username': forms.EmailInput(attrs={
                'placeholder': 'Email',
            }),
            'email': forms.HiddenInput,
        }

    def save(self, commit=True):
        user = super().save(False)
        user.email = user.username
        user = super().save()
        return user