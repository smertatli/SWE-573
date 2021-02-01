from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login
from django.contrib.auth import logout as django_logout
from .forms import UserForm
from django.contrib.auth.models import User
from django.http import HttpResponseRedirect, HttpResponse
from django.urls import reverse_lazy, reverse
from django.conf import settings
from django.views.generic import TemplateView
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.decorators import login_required
import io
import re
import twitter
from collections import OrderedDict



CONSUMER_KEY = "sJJJUWkvfvpZYcbY0buMRYup7"
CONSUMER_SECRET = "iDQB0WGuOsY7ITZCYwZEk2o7a2kxiSKn6kFg3NZFO4ca11LoYA" 
ACCESS_TOKEN = "184983841-Cg8ps0f6pp98lsQRwennlwhilmHpMFQp2TUuciH1"
ACCESS_TOKEN_SECRET = "an8rfv4cyuSLCCaUqfU3zy8RRS55hmGHUvim1FGDJkQlk"


def is_email_occupied(_email):
    user = User.objects.filter(username=_email).exists()
    if user:
        return True
    else:
        return False


def _signup(request):
    error=''
    if request.method == 'POST':
        
        form = UserForm(data = request.POST)
        if is_email_occupied(request.POST.get('email')):
            error = 'Email is in use. Please provide a different email.'

        elif form.is_valid():
            user = form.save()
            password = request.POST.get('password')
            user.set_password(password)
            user.is_active = False
            user.save()

            send_mail_to_admin(request.POST.get('username'))
            return redirect(settings.LOGIN_URL)
        else:
            error = 'Form validation failed.' 
        error = form.errors

    return render(request, 'accounts/signup.html', {
        'error': error 
    })


def _login(request):
    loginFailed = False
    errorMessage = ""
    if request.user.is_authenticated:
        return render(request, 'accounts/board.html')
    elif request.method == 'POST':
        username = request.POST.get('email')
        password = request.POST.get('password')
        user = authenticate(username=username, password=password)
        if user:
            if user.is_active:
                login(request, user)
                return render(request, 'accounts/board.html')
            else:
                loginFailed = True
                errorMessage = "Your account is not actived by the admin yet."
                # return HttpResponse("Your account is not active.")
        else:
            loginFailed = True
            errorMessage = "Invalid login,check your username and password!"
    return render(request, 'accounts/login.html', {'loginFailed': loginFailed,
                                                   'errorMessage': errorMessage
                                                   })
@login_required
def _looknfeel(request):
    return render(request, 'accounts/looknfeel.html')

@csrf_exempt
def _sniff_tweets(request):
    keyword = request.POST.get('keyword')
    start_date = request.POST.get('start')
    end_date = request.POST.get('end')
    api = twitter.Api(consumer_key=CONSUMER_KEY,
                  consumer_secret=CONSUMER_SECRET,
                  access_token_key=ACCESS_TOKEN,
                  access_token_secret=ACCESS_TOKEN_SECRET)
    data = api.GetSearch(term=keyword, count=100, lang='tr', since=start_date, until=end_date ,  include_entities=False, result_type='recent')
    tweets_text = [[tw.id,tw.created_at,tw.text] for tw in data]
    tweets_text = {'data': tweets_text}
    
    return JsonResponse(tweets_text, safe=False)





def send_mail_to_admin(user):
    import smtplib

    try:
        server = smtplib.SMTP_SSL('smtp.gmail.com', 465)
        server.ehlo()
        server.login('trendspotter.info@gmail.com', 'rRocks15')
        server.sendmail('trendspotter.info@gmail.com', 'trendspotter.info@gmail.com', 'User {0} is waiting for activation.'.format(user))
        server.sendmail('trendspotter.info@gmail.com', user, 'Thank you for registering. Your account is waiting for admin approval.')
        
    except Exception as e:
        print ('Something went wrong...', str(e))





def logout(request):
    print('LOG OUTTTT',request.user, request.user.is_authenticated)
    django_logout(request)
    return HttpResponseRedirect('/')

def check_user(request):
    if request.user.is_authenticated:
        return HttpResponseRedirect(reverse('tracker:create_track'))
    else:
        return HttpResponseRedirect(reverse('accounts:login'))