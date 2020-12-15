from django.shortcuts import render
from .models import User
from .forms import UserForm
# Create your views here.


def register(request):
    user_form = UserForm()

    return render(request, 'accounts/register.html',
                  {'user_form': user_form
                   })